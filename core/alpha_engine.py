# core/alpha_engine.py
"""
Động cơ tín hiệu Alpha và backtest.

Backtest được thực hiện theo phương pháp vector hóa, với năm ràng buộc nhằm bảo đảm
đường equity thu được là khả thi trên thị trường thật:

  1. KHÔNG BÁN KHỐNG (mặc định). Thị trường Việt Nam không cho bán khống cổ phiếu,
     nên vị thế bị chặn trong [0; 1]. Ràng buộc này đặc biệt quan trọng với tín hiệu
     hồi quy về trung bình: vì tín hiệu đối xứng quanh 0, nếu cho phép vị thế âm thì
     khoảng một nửa hiệu suất sẽ đến từ giao dịch không thực hiện được.
  2. THANH TOÁN T+2. Cổ phiếu mua phiên T chỉ bán được từ phiên T+2, nên vị thế bị
     giữ tối thiểu hai phiên sau mỗi lệnh mua. Bỏ qua ràng buộc này cho phép chiến
     lược đảo vị thế hằng ngày — một hành vi không tồn tại trên HOSE.
  3. ĐỘ TRỄ KHỚP LỆNH T+1 (signal.shift). Tín hiệu chốt hết phiên T chỉ được khớp ở
     phiên kế tiếp, nhằm loại bỏ sai lệch nhìn trước (look-ahead bias).
  4. PHÂN BIỆT SHARPE VÀ INFORMATION RATIO. Sharpe trừ lãi suất phi rủi ro ở tử số;
     nếu không trừ, đại lượng thu được là Information Ratio so với mốc 0. Cả hai
     được báo cáo riêng để tránh nhầm lẫn khi so sánh với tài liệu.
  5. TỶ LỆ THẮNG TÍNH TRÊN LỆNH. Mỗi lệnh là một chuỗi phiên liên tiếp giữ cùng
     chiều vị thế; tỷ lệ ngày lãi trên tổng số ngày là một đại lượng khác và thường
     cao hơn, nên đơn vị quan sát phải được nêu rõ.

Chi phí giao dịch được tính trên turnover thực tế của từng lần thay đổi vị thế.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.indicators import calculate_rsi
from utils.config import (ALLOW_SHORT, EXECUTION_LAG, RISK_FREE_RATE,
                          SETTLEMENT_LAG, TRADING_DAYS, TRANSACTION_COST)

SIGNALS = ["Momentum_RSI", "Mean_Reversion_ZScore", "Volume_Price_Trend", "Momentum_5D"]


class AlphaEngine:

    # ------------------------------------------------------------------
    @staticmethod
    def calculate_alpha_signal(df: pd.DataFrame, expression_type: str = "Momentum_RSI") -> pd.Series:
        """Sinh tín hiệu trong khoảng [-1, 1]. df cần cột: close, volume."""
        data = df.copy()

        if expression_type == "Momentum_RSI":
            # Đây là tín hiệu THUẬN xu hướng: (rsi − 50)/50 dương khi RSI > 50, tức
            # mua khi động lượng còn dương. Không phải tín hiệu đảo chiều.
            rsi = calculate_rsi(data["close"], period=14)
            signal = (rsi - 50.0) / 50.0

        elif expression_type == "Mean_Reversion_ZScore":
            # ĐẢO CHIỀU: giá lệch xa trung bình 20 phiên thì kỳ vọng quay về
            sma20 = data["close"].rolling(20).mean()
            std20 = data["close"].rolling(20).std(ddof=1)
            signal = -((data["close"] - sma20) / std20.replace(0, np.nan))

        elif expression_type == "Volume_Price_Trend":
            ret = data["close"].pct_change()
            vol_sma = data["volume"].rolling(20).mean()
            signal = ret * (data["volume"] / vol_sma.replace(0, np.nan))

        else:  # Momentum_5D
            signal = data["close"].pct_change(5) * 10

        return signal.clip(-1.0, 1.0).fillna(0.0)

    # ------------------------------------------------------------------
    @staticmethod
    def _apply_settlement(position: np.ndarray, lag: int) -> np.ndarray:
        """
        Ràng buộc T+2: sau khi TĂNG vị thế ở phiên i, không được giảm trong `lag`
        phiên kế tiếp vì cổ phiếu chưa về tài khoản.
        """
        if lag <= 0:
            return position
        pos = position.copy()
        last_buy = -(10**9)
        for i in range(1, len(pos)):
            if pos[i] > pos[i - 1]:
                last_buy = i
            elif pos[i] < pos[i - 1] and (i - last_buy) <= lag:
                pos[i] = pos[i - 1]          # chưa về hàng -> giữ nguyên
        return pos

    # ------------------------------------------------------------------
    @staticmethod
    def backtest_signal(
        df: pd.DataFrame,
        signal: pd.Series,
        initial_capital: float = 100_000_000.0,
        transaction_cost: float = TRANSACTION_COST,
        allow_short: bool = ALLOW_SHORT,
        execution_lag: int = EXECUTION_LAG,
        settlement_lag: int = SETTLEMENT_LAG,
    ) -> dict:
        """Backtest vector hóa, có phí, có ràng buộc vi cấu trúc thị trường VN."""
        if df.empty or len(df) < 30:
            raise ValueError(f"Chỉ có {len(df)} phiên — quá ít để backtest (cần ≥ 30).")

        data = df.copy()
        data["signal"] = signal.reindex(data.index).fillna(0.0)

        # shift(execution_lag): tín hiệu chốt hết phiên T, khớp lệnh phiên T+1.
        # Ràng buộc chống look-ahead: tín hiệu của phiên T chỉ tác động từ phiên T+1.
        lower = -1.0 if allow_short else 0.0        # long-only cho thị trường VN
        pos = data["signal"].shift(execution_lag).fillna(0.0).clip(lower, 1.0).to_numpy()
        data["position"] = AlphaEngine._apply_settlement(pos, settlement_lag)

        data["turnover"] = data["position"].diff().abs().fillna(0.0)
        data["market_return"] = data["close"].pct_change().fillna(0.0)
        data["strategy_return"] = (data["position"] * data["market_return"]
                                   - data["turnover"] * transaction_cost)

        data["cum_market_return"] = (1 + data["market_return"]).cumprod()
        data["cum_strategy_return"] = (1 + data["strategy_return"]).cumprod()
        data["equity"] = initial_capital * data["cum_strategy_return"]

        n = len(data)
        total_return = float(data["cum_strategy_return"].iloc[-1] - 1)
        ann_return = (1 + total_return) ** (TRADING_DAYS / n) - 1

        daily = data["strategy_return"]
        std = float(daily.std(ddof=1))
        rf_d = RISK_FREE_RATE / TRADING_DAYS

        # Sharpe ĐÚNG: có trừ lãi suất phi rủi ro
        sharpe = ((daily.mean() - rf_d) / std) * np.sqrt(TRADING_DAYS) if std > 0 else 0.0
        # Information Ratio: cùng dạng với Sharpe nhưng KHÔNG trừ lãi suất phi rủi ro
        info_ratio = (daily.mean() / std) * np.sqrt(TRADING_DAYS) if std > 0 else 0.0

        downside = daily[daily < 0].std(ddof=1)
        sortino = ((daily.mean() - rf_d) / downside) * np.sqrt(TRADING_DAYS) if downside > 0 else np.nan

        cum_max = data["equity"].cummax()
        max_drawdown = float(((data["equity"] - cum_max) / cum_max).min())

        # ---- Tỷ lệ thắng tính trên LỆNH, không phải trên NGÀY ----
        sign = np.sign(data["position"])
        block = (sign != sign.shift()).cumsum()
        mask = sign != 0
        if mask.any():
            trade_ret = (data.loc[mask, "strategy_return"]
                         .groupby(block[mask])
                         .apply(lambda s: float((1 + s).prod() - 1)))
            win_rate = float((trade_ret > 0).mean())
            n_trades = int(len(trade_ret))
            avg_hold = float(mask.sum() / n_trades) if n_trades else 0.0
        else:
            trade_ret, win_rate, n_trades, avg_hold = pd.Series(dtype=float), 0.0, 0, 0.0

        bh_return = float(data["cum_market_return"].iloc[-1] - 1)

        return {
            "data": data,
            "total_return": total_return,
            "ann_return": float(ann_return),
            "sharpe_ratio": float(sharpe),
            "information_ratio": float(info_ratio),
            "sortino_ratio": float(sortino) if sortino == sortino else np.nan,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,               # TRÊN LỆNH
            "n_trades": n_trades,
            "avg_holding_days": avg_hold,
            "trade_returns": trade_ret,
            "total_turnover": float(data["turnover"].sum()),
            "total_cost": float(data["turnover"].sum() * transaction_cost * initial_capital),
            "final_equity": float(data["equity"].iloc[-1]),
            "benchmark_return": bh_return,
            "excess_vs_benchmark": total_return - bh_return,
            "assumptions": {
                "allow_short": allow_short,
                "execution_lag": execution_lag,
                "settlement_lag": settlement_lag,
                "transaction_cost": transaction_cost,
            },
        }
