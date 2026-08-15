"""Test backtest engine, mô hình chi phí, ràng buộc rủi ro và metrics."""
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from luca_quant.backtest.engine import BacktestEngine
from luca_quant.config.settings import CostConfig, RiskConfig
from luca_quant.data.providers.synthetic import SyntheticProvider
from luca_quant.evaluation.metrics import MetricsEngine
from luca_quant.risk.manager import RiskConstraints, RiskConstraintViolation
from luca_quant.risk.overlay import HurstOverlay, MACDOverlay, OverlayStack


@pytest.fixture(scope="module")
def prices():
    return SyntheticProvider(seed=3).get_ohlcv("TEST", datetime(2018, 1, 1), datetime(2024, 12, 31))


def test_execution_lag_prevents_lookahead():
    """
    Tín hiệu tại t phải sinh lợi suất của t+1, không phải của t.

    Dựng chuỗi giá chỉ tăng đúng MỘT phiên. Đặt tín hiệu tại phiên NGAY TRƯỚC
    cú tăng -> phải ăn được. Đặt tín hiệu tại chính phiên tăng -> KHÔNG được
    ăn (vì khi đó đã quá muộn).
    """
    idx = pd.bdate_range("2020-01-01", periods=10)
    close = np.full(10, 100.0)
    close[5:] = 110.0                              # cú tăng xảy ra tại i=5
    px = pd.DataFrame({"open": close, "high": close, "low": close,
                       "close": close, "volume": 1e6}, index=idx)

    eng = BacktestEngine(CostConfig(commission_buy=0, commission_sell=0,
                                    sell_tax=0, slippage_bps=0, settlement_days=0))

    good = pd.Series(0.0, index=idx); good.iloc[4] = 1.0     # biết trước tại i=4
    bad = pd.Series(0.0, index=idx); bad.iloc[5] = 1.0       # biết tại i=5 (đã muộn)

    assert eng.run(px, good).returns.iloc[5] == pytest.approx(0.10, abs=1e-9)
    assert eng.run(px, bad).returns.iloc[5] == pytest.approx(0.0, abs=1e-9)


def test_sell_costs_more_than_buy():
    """TTCK VN: bán phải chịu thêm thuế 0.1%. Repo cũ dùng phí đối xứng."""
    c = CostConfig()
    assert c.sell_cost > c.buy_cost
    assert c.sell_cost == pytest.approx(0.0015 + 0.001 + 0.0005)


def test_long_only_by_default(prices):
    eng = BacktestEngine()
    sig = pd.Series(-1.0, index=prices.index)
    assert (eng.run(prices, sig).positions >= 0).all()


def test_costs_reduce_returns(prices):
    """Chiến lược đảo vị thế mỗi phiên phải bị chi phí ăn mòn."""
    sig = pd.Series(np.tile([0.0, 1.0], len(prices) // 2 + 1)[:len(prices)],
                    index=prices.index)
    free = BacktestEngine(CostConfig(commission_buy=0, commission_sell=0,
                                     sell_tax=0, slippage_bps=0, settlement_days=0))
    real = BacktestEngine(CostConfig())
    assert real.run(prices, sig).returns.sum() < free.run(prices, sig).returns.sum()
    assert real.run(prices, sig).cost_drag > 0


def test_settlement_blocks_immediate_sell():
    """T+2: mua tại t thì t+1 chưa được bán."""
    idx = pd.bdate_range("2020-01-01", periods=12)
    px = pd.DataFrame({"open": 100.0, "high": 100.0, "low": 100.0,
                       "close": 100.0, "volume": 1e6}, index=idx)
    sig = pd.Series(0.0, index=idx)
    sig.iloc[2] = 1.0                              # mua
    sig.iloc[3] = 0.0                              # muốn bán ngay hôm sau
    eng = BacktestEngine(CostConfig(settlement_days=2))
    pos = eng.run(px, sig, apply_settlement=True).positions
    assert pos.iloc[4] == pytest.approx(1.0), "T+2 phải chặn lệnh bán quá sớm"


def test_risk_constraints_can_only_reduce(prices):
    """
    BẤT BIẾN CỐT LÕI. RiskManager của repo cũ vi phạm điều này bằng dòng
    `data.loc[entry_mask, signal_col] = self.max_exposure` (all-in).
    """
    rc = RiskConstraints(RiskConfig(target_volatility=0.15, max_drawdown_stop=0.2))
    raw = pd.Series(np.random.default_rng(0).uniform(0, 1, len(prices)), index=prices.index)
    final, _ = rc.apply(raw, prices)
    assert (final <= raw + 1e-9).all()
    assert (final >= -1e-9).all()


def test_overlay_multiplier_within_unit_interval(prices):
    """Overlay chỉ được điều tiết trong [0,1] — không được tự tạo vị thế."""
    feats = pd.DataFrame({"fractal__hurst_50": 0.4}, index=prices.index)
    stack = OverlayStack([HurstOverlay(), MACDOverlay()])
    raw = pd.Series(0.6, index=prices.index)
    out = stack.apply(raw, prices, feats)
    assert (out <= raw + 1e-12).all() and (out >= 0).all()


def test_single_sharpe_definition():
    """
    Repo cũ có hai công thức Sharpe khác nhau. Test này khoá lại đúng một
    định nghĩa: mean/std của lợi suất VƯỢT TRỘI, nhân sqrt(252).
    """
    rng = np.random.default_rng(1)
    r = pd.Series(rng.normal(0.0006, 0.012, 1500))
    me = MetricsEngine(risk_free_rate=0.045)
    expected = (r - me.rf_daily).mean() / (r - me.rf_daily).std(ddof=1) * np.sqrt(252)
    assert me.compute(r)["Sharpe"] == pytest.approx(expected, rel=1e-9)


def test_risk_free_rate_lowers_sharpe():
    rng = np.random.default_rng(2)
    r = pd.Series(rng.normal(0.0008, 0.011, 1200))
    assert MetricsEngine(0.045).compute(r)["Sharpe"] < MetricsEngine(0.0).compute(r)["Sharpe"]


def test_buy_and_hold_matches_market(prices):
    bt = BacktestEngine(CostConfig(commission_buy=0, commission_sell=0,
                                   sell_tax=0, slippage_bps=0))
    res = bt.buy_and_hold(prices)
    assert res.returns.iloc[2:].sub(res.data["market_return"].iloc[2:]).abs().max() < 1e-12
