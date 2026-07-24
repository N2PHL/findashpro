# core/portfolio_opt.py
import numpy as np
import pandas as pd
from scipy.optimize import minimize

class PortfolioOptimizer:
    """
    Module Tối ưu hóa Danh mục (Mean-Variance) & Đánh giá Rủi ro (VaR / CVaR).
    """
    @staticmethod
    def calculate_performance(weights: np.ndarray, mean_returns: pd.Series, cov_matrix: pd.DataFrame, risk_free_rate: float = 0.04):
        """Tính Lợi nhuận kỳ vọng, Độ lệch chuẩn và Sharpe Ratio của danh mục."""
        p_ret = np.sum(mean_returns * weights) * 252
        p_std = np.sqrt(np.dot(weights.T, np.dot(cov_matrix * 252, weights)))
        sharpe = (p_ret - risk_free_rate) / (p_std + 1e-9)
        return p_ret, p_std, sharpe

    @classmethod
    def optimize_sharpe(cls, mean_returns: pd.Series, cov_matrix: pd.DataFrame, risk_free_rate: float = 0.04) -> np.ndarray:
        """Tối ưu hóa tìm Tỷ trọng (Weights) đạt Sharpe Ratio lớn nhất."""
        num_assets = len(mean_returns)
        
        def neg_sharpe(weights):
            _, _, sharpe = cls.calculate_performance(weights, mean_returns, cov_matrix, risk_free_rate)
            return -sharpe

        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1.0})
        bounds = tuple((0.0, 1.0) for _ in range(num_assets))
        init_weights = num_assets * [1.0 / num_assets]

        res = minimize(neg_sharpe, init_weights, method='SLSQP', bounds=bounds, constraints=constraints)
        return res.x

    @classmethod
    def generate_efficient_frontier(cls, mean_returns: pd.Series, cov_matrix: pd.DataFrame, num_portfolios: int = 1500):
        """Mô phỏng Monte Carlo tạo Đường biên hiệu quả (Efficient Frontier)."""
        num_assets = len(mean_returns)
        results = np.zeros((3, num_portfolios))
        
        for i in range(num_portfolios):
            weights = np.random.random(num_assets)
            weights /= np.sum(weights)
            
            p_ret, p_std, sharpe = cls.calculate_performance(weights, mean_returns, cov_matrix)
            results[0, i] = p_std
            results[1, i] = p_ret
            results[2, i] = sharpe

        return results

    @staticmethod
    def calculate_var_cvar(returns: pd.Series, confidence_level: float = 0.95, capital: float = 100_000_000) -> dict:
        """
        Tính toán Value at Risk (VaR) & Conditional Value at Risk (CVaR / Expected Shortfall).
        """
        sorted_returns = returns.sort_values()
        index = int((1 - confidence_level) * len(sorted_returns))
        
        var_pct = -sorted_returns.iloc[index]
        cvar_pct = -sorted_returns.iloc[:index].mean()
        
        return {
            'var_pct': var_pct,
            'var_amount': var_pct * capital,
            'cvar_pct': cvar_pct,
            'cvar_amount': cvar_pct * capital,
            'confidence': confidence_level
        }
    