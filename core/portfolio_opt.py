# core/portfolio_opt.py
"""
Tối ưu hóa danh mục Mean-Variance và đo lường rủi ro VaR / CVaR.

Bốn yêu cầu về phương pháp:

  1. LÃI SUẤT PHI RỦI RO ĐỌC TỪ utils.config, không khai báo tại chỗ. Nếu module này
     và trang phân tích rủi ro dùng hai giá trị khác nhau, Sharpe ratio ở đây và lợi
     suất yêu cầu theo CAPM ở đó sẽ không so sánh được với nhau.

  2. ĐƯỜNG BIÊN HIỆU QUẢ ĐƯỢC GIẢI BẰNG TỐI ƯU, không lấy bao lồi của đám mây điểm
     ngẫu nhiên. Hàm efficient_frontier() giải bài toán quy hoạch toàn phương tại
     từng mức lợi suất mục tiêu. Lý do không dùng phương pháp lấy mẫu: trọng số sinh
     từ phân phối đều rồi chuẩn hóa sẽ tập trung quanh danh mục cân bằng đều; với
     n = 4 mã, xác suất một trọng số vượt 0,9 chỉ khoảng 0,025%, nên trong 1.500 lần
     rút, kỳ vọng số điểm chạm được đầu mút đường biên là 0,4 — tức gần như không bao
     giờ. Đám mây ngẫu nhiên vì vậy ước lượng thiếu tập cơ hội một cách hệ thống và
     chỉ nên dùng để minh họa hình dạng tập khả thi.

  3. VaR VÀ CVaR CÓ KIỂM TRA CỠ MẪU. Với mẫu nhỏ, chỉ số phân vị int(0.05 × n) có thể
     bằng 0, khiến trung bình vùng đuôi trở thành NaN và VaR suy biến thành mức lỗ
     cực đại thay vì phân vị 5%. Hàm báo lỗi tường minh thay vì trả NaN im lặng.

  4. KIỂM TRA HỘI TỤ CỦA BỘ TỐI ƯU. Kết quả của minimize() chỉ được dùng khi
     res.success là True; nếu không, bài toán được coi là vô nghiệm thay vì vẽ đồ thị
     từ một nghiệm chưa hội tụ.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy import stats

from utils.config import RANDOM_SEED, RISK_FREE_RATE, TRADING_DAYS

MIN_OBS_VAR = 100


# ---------------------------------------------------------------------------
# LEDOIT–WOLF SHRINKAGE
# ---------------------------------------------------------------------------
def ledoit_wolf_shrinkage(returns: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    """
    Co ma trận hiệp phương sai mẫu về mục tiêu tương quan hằng số.

    Vấn đề: ma trận hiệp phương sai mẫu ước lượng N(N+1)/2 tham số từ T quan sát.
    Với 6 mã và 250 phiên, đó là 21 tham số từ 250 điểm — sai số ước lượng lớn, và
    bộ tối ưu mean-variance KHUẾCH ĐẠI chính sai số đó: nó dồn trọng số vào đúng
    những cặp tài sản mà hiệp phương sai bị ước lượng thấp một cách ngẫu nhiên.
    Đây là lý do danh mục "tối ưu" thường có trọng số cực đoan và hoạt động kém
    ngoài mẫu — hiện tượng được gọi là "cỗ máy tối đa hóa sai số ước lượng".

    Cách xử lý (Ledoit & Wolf, 2003, "Honey, I Shrunk the Sample Covariance Matrix"):
    lấy tổ hợp lồi giữa ma trận mẫu S và một mục tiêu F có cấu trúc chặt hơn:

        Σ* = δ·F + (1 − δ)·S

    F ở đây là ma trận tương quan hằng số: giữ nguyên phương sai từng mã, thay mọi
    hệ số tương quan bằng trung bình của chúng. F rất chệch nhưng gần như không có
    nhiễu; S không chệch nhưng đầy nhiễu. Hệ số δ tối ưu được ước lượng từ chính dữ
    liệu bằng cách tối thiểu hóa sai số bình phương kỳ vọng, KHÔNG phải chọn tay.

    Trả về (ma trận đã co, δ). δ gần 1 nghĩa là mẫu quá nhiễu để tin cậy.
    """
    X = np.asarray(returns.dropna(), dtype=float)
    t, n = X.shape
    if t < 2 or n < 2:
        return returns.cov(), 0.0

    X = X - X.mean(axis=0)
    S = (X.T @ X) / t                                  # hiệp phương sai mẫu (MLE)

    var = np.diag(S)
    std = np.sqrt(var)
    outer_std = np.outer(std, std)

    corr = S / outer_std
    r_bar = (corr.sum() - n) / (n * (n - 1))           # tương quan trung bình
    F = r_bar * outer_std
    np.fill_diagonal(F, var)                           # mục tiêu giữ nguyên phương sai

    # pi: tổng phương sai của từng phần tử trong S
    X2 = X**2
    pi_mat = (X2.T @ X2) / t - S**2
    pi = pi_mat.sum()

    # rho: phần hiệp phương sai giữa S và F (công thức tương quan hằng số)
    term = ((X**3).T @ X) / t - var * S
    rho = np.diag(pi_mat).sum() + r_bar * (
        (np.outer(1.0 / std, std) * term + np.outer(std, 1.0 / std) * term.T).sum()
        - np.diag((np.outer(1.0 / std, std) * term
                   + np.outer(std, 1.0 / std) * term.T)).sum()
    ) / 2.0

    gamma = float(((F - S) ** 2).sum())                # độ chệch của mục tiêu
    kappa = (pi - rho) / gamma if gamma > 0 else 0.0
    delta = float(np.clip(kappa / t, 0.0, 1.0))        # hệ số co tối ưu

    shrunk = delta * F + (1 - delta) * S
    # Quy về ước lượng không chệch cho mẫu (S ở trên dùng mẫu số t)
    shrunk = shrunk * t / (t - 1)

    return pd.DataFrame(shrunk, index=returns.columns, columns=returns.columns), delta


COV_METHODS = {
    "Hiệp phương sai mẫu": "sample",
    "Ledoit–Wolf shrinkage": "ledoit_wolf",
}


def covariance_matrix(returns: pd.DataFrame,
                      method: str = "ledoit_wolf") -> tuple[pd.DataFrame, float]:
    """Cổng vào duy nhất để lấy ma trận hiệp phương sai. Trả về (Σ, δ)."""
    if method == "sample":
        return returns.cov(), 0.0
    if method == "ledoit_wolf":
        return ledoit_wolf_shrinkage(returns)
    raise ValueError(f"method không hợp lệ: {method!r}")


class PortfolioOptimizer:
    """Tất cả tham số lợi suất đầu vào là LOG return theo phiên."""

    # ---------------- Hiệu năng ----------------
    @staticmethod
    def calculate_performance(weights, mean_returns, cov_matrix,
                              risk_free_rate: float = RISK_FREE_RATE):
        w = np.asarray(weights, dtype=float)
        p_ret = float(np.dot(mean_returns, w) * TRADING_DAYS)
        p_std = float(np.sqrt(w @ (np.asarray(cov_matrix) * TRADING_DAYS) @ w))
        sharpe = (p_ret - risk_free_rate) / p_std if p_std > 1e-12 else np.nan
        return p_ret, p_std, sharpe

    # ---------------- Tối ưu ----------------
    @classmethod
    def _solve(cls, objective, n_assets, extra_constraints=(), max_weight: float = 1.0):
        cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}, *extra_constraints]
        bounds = tuple((0.0, max_weight) for _ in range(n_assets))  # long-only: TTCK VN không bán khống
        res = minimize(objective, np.repeat(1.0 / n_assets, n_assets),
                       method="SLSQP", bounds=bounds, constraints=cons,
                       options={"maxiter": 500, "ftol": 1e-10})
        if not res.success:
            raise RuntimeError(f"Bộ tối ưu SLSQP không hội tụ: {res.message}")
        return res.x

    @classmethod
    def optimize_sharpe(cls, mean_returns, cov_matrix,
                        risk_free_rate: float = RISK_FREE_RATE,
                        max_weight: float = 1.0) -> np.ndarray:
        def neg_sharpe(w):
            return -cls.calculate_performance(w, mean_returns, cov_matrix, risk_free_rate)[2]
        return cls._solve(neg_sharpe, len(mean_returns), max_weight=max_weight)

    @classmethod
    def optimize_min_variance(cls, mean_returns, cov_matrix,
                              max_weight: float = 1.0) -> np.ndarray:
        cov = np.asarray(cov_matrix) * TRADING_DAYS
        return cls._solve(lambda w: float(w @ cov @ w), len(mean_returns), max_weight=max_weight)

    # ---------------- Đường biên hiệu quả THẬT ----------------
    @classmethod
    def efficient_frontier(cls, mean_returns, cov_matrix,
                           n_points: int = 40, max_weight: float = 1.0) -> pd.DataFrame:
        """
        Với MỖI mức lợi suất mục tiêu R*, giải:
            min  wᵀΣw   s.t.  Σw = 1,  wᵀμ = R*,  0 ≤ w ≤ max_weight

        Đây mới là đường biên hiệu quả. Rắc N bộ trọng số ngẫu nhiên chỉ cho ra một
        đám mây tụ quanh danh mục đều và gần như không bao giờ chạm hai đầu mút.
        """
        n = len(mean_returns)
        ann_mu = np.asarray(mean_returns) * TRADING_DAYS
        ann_cov = np.asarray(cov_matrix) * TRADING_DAYS

        lo = float(cls.calculate_performance(
            cls.optimize_min_variance(mean_returns, cov_matrix, max_weight),
            mean_returns, cov_matrix)[0])
        # Cận trên phải là lợi suất cao nhất CÒN KHẢ THI dưới ràng buộc trần tỷ trọng,
        # không phải lợi suất của mã tốt nhất. Với max_weight = 0.4 và 4 mã, danh mục
        # không thể dồn 100% vào một mã, nên mọi mức mục tiêu phía trên cận khả thi đều
        # vô nghiệm và bộ tối ưu trả về chuỗi thất bại — đường biên khi đó bị cụt.
        # Danh mục lợi suất cao nhất giải được bằng tay: rót đủ trần vào các mã có μ lớn
        # nhất theo thứ tự giảm dần cho tới khi hết 100% trọng số.
        w_max = np.zeros(n)
        remaining = 1.0
        for i in np.argsort(ann_mu)[::-1]:
            take = min(max_weight, remaining)
            w_max[i] = take
            remaining -= take
            if remaining <= 1e-12:
                break
        hi = float(w_max @ ann_mu)

        if hi <= lo:
            hi = lo * 1.05 + 1e-6

        rows = []
        for target in np.linspace(lo, hi, n_points):
            cons = ({"type": "eq", "fun": lambda w, t=target: float(w @ ann_mu) - t},)
            try:
                w = cls._solve(lambda w: float(w @ ann_cov @ w), n, cons, max_weight)
            except RuntimeError:
                continue                              # bỏ điểm không hội tụ, không im lặng nuốt lỗi
            ret, std, sharpe = cls.calculate_performance(w, mean_returns, cov_matrix)
            rows.append({"ret": ret, "vol": std, "sharpe": sharpe, "weights": w})

        if not rows:
            raise RuntimeError("Không giải được điểm nào trên đường biên hiệu quả.")
        return pd.DataFrame(rows)

    @classmethod
    def random_portfolios(cls, mean_returns, cov_matrix, n: int = 1500,
                          seed: int | None = RANDOM_SEED) -> pd.DataFrame:
        """
        Đám mây danh mục ngẫu nhiên — GỌI ĐÚNG TÊN, chỉ để làm nền minh họa.
        Dùng Dirichlet để phủ không gian trọng số đều hơn np.random.random() chuẩn hóa,
        và có seed để đám mây không nhảy mỗi lần rerun.
        """
        rng = np.random.default_rng(seed)
        n_assets = len(mean_returns)
        w = rng.dirichlet(np.ones(n_assets) * 0.6, size=n)   # alpha<1: phủ cả vùng tập trung
        out = [cls.calculate_performance(wi, mean_returns, cov_matrix) for wi in w]
        return pd.DataFrame(out, columns=["ret", "vol", "sharpe"])

    # ---------------- VaR / CVaR ----------------
    @staticmethod
    def calculate_var_cvar(returns: pd.Series, confidence_level: float = 0.95,
                           capital: float = 100_000_000) -> dict:
        """
        VaR lịch sử + VaR tham số (chuẩn) để đối chiếu.

        Ba sửa lỗi:
          - np.percentile CÓ nội suy tuyến tính, chính xác hơn iloc[int((1-c)*n)]
          - đuôi để tính CVaR BAO GỒM chính điểm VaR (r <= VaR); dùng
            .iloc[:index] nên vừa loại nhầm điểm VaR vừa trả NaN khi index = 0
          - CHẶN mẫu nhỏ bằng ValueError thay vì hiển thị một con số vô nghĩa
        """
        r = pd.Series(returns).dropna()
        n = len(r)
        alpha = 1 - confidence_level

        if n < MIN_OBS_VAR:
            raise ValueError(
                f"Chỉ có {n} quan sát. VaR lịch sử ở mức {confidence_level:.0%} cần "
                f"ít nhất {MIN_OBS_VAR} quan sát — hiện vùng đuôi chỉ có khoảng "
                f"{int(n * alpha)} điểm, không đủ để ước lượng."
            )

        var_ret = float(np.percentile(r, alpha * 100))
        tail = r[r <= var_ret]
        cvar_ret = float(tail.mean())

        # VaR tham số: giả định chuẩn. So sánh với VaR lịch sử cho thấy đuôi dày.
        z = stats.norm.ppf(alpha)
        var_param = float(r.mean() + z * r.std(ddof=1))

        return {
            "var_pct": -var_ret,
            "var_amount": -var_ret * capital,
            "cvar_pct": -cvar_ret,
            "cvar_amount": -cvar_ret * capital,
            "var_param_pct": -var_param,
            "n_obs": n,
            "n_tail": len(tail),
            "confidence": confidence_level,
        }

    @staticmethod
    def kupiec_test(returns: pd.Series, var_pct: float, confidence_level: float = 0.95) -> dict:
        """
        Kiểm định Kupiec (POF): số lần lỗ vượt VaR có đúng bằng kỳ vọng không?

        Cần thiết vì VaR ở đây được tính trên CHÍNH chuỗi dữ liệu đã dùng để tối ưu
        trọng số — tức VaR in-sample, luôn lạc quan hơn thực tế một cách có hệ thống.
        """
        r = pd.Series(returns).dropna()
        n, p = len(r), 1 - confidence_level
        x = int((r < -var_pct).sum())
        if x == 0 or x == n:
            return {"n": n, "violations": x, "expected": n * p, "lr": np.nan, "pvalue": np.nan}
        pi = x / n
        lr = -2 * ((n - x) * np.log(1 - p) + x * np.log(p)
                   - (n - x) * np.log(1 - pi) - x * np.log(pi))
        return {"n": n, "violations": x, "expected": n * p,
                "lr": float(lr), "pvalue": float(1 - stats.chi2.cdf(lr, df=1))}
