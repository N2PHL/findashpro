"""
Bộ test chống rò rỉ dữ liệu — phần quan trọng nhất của toàn bộ test suite.

Nếu một test ở đây fail, mọi con số Sharpe trong báo cáo đều vô giá trị.
"""
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from luca_quant.data.providers.synthetic import SyntheticProvider
from luca_quant.features.pipeline import FeaturePipeline, build_common_matrix
from luca_quant.features import registry as freg
from luca_quant.labels.registry import make_label
from luca_quant.validation.leakage import LeakageDetector
from luca_quant.validation.splits import PurgedWalkForward


@pytest.fixture(scope="module")
def prices():
    p = SyntheticProvider(mode="random_walk", seed=7)
    return p.get_ohlcv("TEST", datetime(2015, 1, 1), datetime(2024, 12, 31))


ALL_GROUPS = ["price", "trend", "momentum", "volatility", "volume", "fractal", "regime"]


def test_every_feature_is_causal(prices):
    """
    POINT-IN-TIME RECONSTRUCTION.

    Cắt chuỗi giá tại t, tính lại feature -> phải trùng với giá trị tại t
    khi tính trên chuỗi đầy đủ. Đây là bằng chứng thực nghiệm rằng không
    feature nào nhìn tương lai.
    """
    pipe = FeaturePipeline(ALL_GROUPS)
    label = make_label("direction", prices, horizon=1).series
    X, y, _ = build_common_matrix(prices, ALL_GROUPS, label)
    det = LeakageDetector(horizon=5)
    res = det.run_all(
        X=X, y=y,
        raw_df=prices,
        feature_fn=lambda d: pipe.build(d),
    )
    pit = [c for c in res.checks if c["check"] == "point_in_time_causality"][0]
    assert pit["status"] == "PASS", pit["detail"]


def test_no_target_column_in_features(prices):
    pipe = FeaturePipeline(ALL_GROUPS)
    X = pipe.build(prices)
    banned = ("future", "label", "target", "forward")
    assert not [c for c in X.columns if any(b in c.lower() for b in banned)]


def test_purge_gap_covers_label_horizon():
    """gap giữa các segment phải >= horizon, nếu không nhãn train nhìn sang valid."""
    horizon = 10
    cv = PurgedWalkForward(n_splits=4, purge_days=horizon, embargo_days=5, min_train_size=250)
    folds = list(cv.split(2000))
    assert folds
    for f in folds:
        assert f.valid_idx[0] - f.train_idx[-1] - 1 >= horizon
        assert f.test_idx[0] - f.valid_idx[-1] - 1 >= horizon


def test_splits_are_disjoint_and_chronological():
    cv = PurgedWalkForward(n_splits=5, min_train_size=250)
    for f in cv.split(2500):
        tr, va, te = set(f.train_idx), set(f.valid_idx), set(f.test_idx)
        assert not (tr & va) and not (tr & te) and not (va & te)
        assert max(tr) < min(va) < max(va) < min(te)


def test_common_index_across_ablation_scenarios(prices):
    """
    LỖI CỦA REPO CŨ: mỗi kịch bản ablation dropna riêng -> khác số hàng
    -> so sánh Sharpe giữa các kịch bản là so hai giai đoạn thị trường khác nhau.
    """
    label = make_label("direction", prices, horizon=1).series
    X, y, pipe = build_common_matrix(prices, ALL_GROUPS, label)

    scenarios = [["price"], ["price", "trend"], ALL_GROUPS]
    lengths = {len(X[pipe.columns_for(s)]) for s in scenarios}
    assert len(lengths) == 1, f"Các kịch bản có số hàng khác nhau: {lengths}"
    assert not X.isna().any().any()


def test_label_horizon_drops_tail(prices):
    """Nhãn horizon h phải làm mất đúng h quan sát cuối — không được fillna."""
    for h in (1, 5, 20):
        s = make_label("direction", prices, horizon=h).series
        assert s.iloc[-h:].isna().all()
        assert s.iloc[:-h].notna().all()


def test_random_walk_gives_no_alpha(prices):
    """
    NEGATIVE CONTROL — bài kiểm tra thuyết phục nhất.

    Trên random walk thuần không tồn tại alpha. Nếu pipeline vẫn cho AUC
    cao hơn hẳn 0.5 ngoài mẫu thì chắc chắn có rò rỉ ở đâu đó.
    """
    from luca_quant.config.settings import Settings
    from luca_quant.experiments.runner import ExperimentRunner

    label = make_label("direction", prices, horizon=1).series
    X, y, pipe = build_common_matrix(prices, ["price", "trend", "momentum"], label)

    s = Settings()
    s.split.n_splits = 3
    res = ExperimentRunner(s).run(prices.loc[X.index], X, y,
                                  model_name="hist_gb",
                                  feature_groups=["price", "trend", "momentum"])
    auc = res.ml_metrics.get("AUC", 0.5)
    assert 0.40 < auc < 0.62, (
        f"AUC = {auc:.3f} trên dữ liệu KHÔNG có tín hiệu. "
        "Giá trị lệch xa 0.5 là dấu hiệu rò rỉ dữ liệu."
    )
