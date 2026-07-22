# indicators.py module
import pandas as pd

def calculate_sma(df: pd.DataFrame, window: int = 50, column: str = 'Close') -> pd.Series:
    """Tính toán Đường trung bình động đơn giản (SMA)."""
    return df[column].rolling(window=window).mean()
