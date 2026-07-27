# data/dnse_client.py
import requests
import pandas as pd

def fetch_historical_data(ticker: str, start_timestamp: int, end_timestamp: int, resolution: str = '1D', is_index: bool = False) -> pd.DataFrame:
    """
    Lấy dữ liệu giá từ API DNSE.
    Bản hợp nhất: Hỗ trợ is_index (cho mô hình Quant) và trả về đủ OHLCV (cho giao diện Chart/Summary).
    """
    # 1. Định tuyến linh hoạt giữa cổ phiếu và chỉ số
    endpoint = "index" if is_index else "stock"
    url = f"https://services.entrade.com.vn/chart-api/v2/ohlcs/{endpoint}"
    
    params = {
        "symbol": ticker,
        "from": start_timestamp,
        "to": end_timestamp,
        "resolution": resolution
    }
    
    try:
        response = requests.get(url, params=params, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        data = response.json()
        
        if not data or 't' not in data or len(data['t']) == 0:
            return pd.DataFrame()
            
        # 2. Giữ lại toàn bộ cấu trúc OHLCV để trang Summary không bị lỗi KeyError
        df = pd.DataFrame({
            'Date': pd.to_datetime(data['t'], unit='s'),
            'Open': data['o'],
            'High': data['h'],
            'Low': data['l'],
            'Close': data['c'],
            'Volume': data.get('v', [0] * len(data['t'])) # Dùng get() để chống lỗi nếu API không có Volume
        })
        
        # 3. Chuẩn hóa Index để ghép nối ma trận ở các trang Quant không bị lệch dòng
        df['Date'] = df['Date'].dt.tz_localize(None).dt.normalize()
        df.set_index('Date', inplace=True)
        
        return df
        
    except Exception as e:
        print(f"Lỗi khi lấy dữ liệu cho mã {ticker}: {e}")
        return pd.DataFrame()
    