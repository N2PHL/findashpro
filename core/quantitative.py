# quantitative.py module
import numpy as np
import pandas as pd

def run_monte_carlo(close_prices: pd.Series, time_horizon: int, simulations: int) -> pd.DataFrame:
    """Chạy mô phỏng Monte Carlo dự báo giá cổ phiếu."""
    daily_return = close_prices.pct_change().dropna()
    daily_volatility = np.std(daily_return)
    last_price = close_prices.iloc[-1]
    
    simulation_df = pd.DataFrame()
    
    for i in range(simulations):
        future_returns = np.random.normal(0, daily_volatility, time_horizon)
        price_paths = last_price * np.cumprod(1 + future_returns)
        simulation_df[i] = price_paths
        
    return simulation_df
