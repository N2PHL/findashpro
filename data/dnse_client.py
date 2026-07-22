# dnse_client.py module
# data/dnse_client.py
import requests
import pandas as pd
from datetime import datetime

def fetch_historical_data(ticker: str, start_timestamp: int, end_timestamp: int, resolution: str = '1D') -> pd.DataFrame:
    """
    Lấy dữ liệu giá lịch sử từ API của DNSE.
    """
    url = "https://services.entrade.com.vn/chart-api/v2/ohlcs/stock"
    params = {
        "symbol": ticker,
        "from": start_timestamp,
        "to": end_timestamp,
        "resolution": resolution
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Xử lý trường hợp không có dữ liệu
        if not data or 't' not in data:
            return pd.DataFrame()
            
        # Chuyển đổi JSON sang Pandas DataFrame
        df = pd.DataFrame({
            'Date': pd.to_datetime(data['t'], unit='s'), # 't' là timestamp
            'Open': data['o'],
            'High': data['h'],
            'Low': data['l'],
            'Close': data['c'],
            'Volume': data['v']
        })
        df.set_index('Date', inplace=True)
        return df
        
    except Exception as e:
        # Tích hợp logger sau
        print(f"Lỗi khi lấy dữ liệu cho mã {ticker}: {e}")
        return pd.DataFrame()
        