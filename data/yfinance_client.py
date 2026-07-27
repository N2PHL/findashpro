# data/yfinance_client.py
import yfinance as yf
import pandas as pd

def fetch_financial_ratios(ticker: str) -> pd.DataFrame:
    """
    Kéo các chỉ số định giá cơ bản từ Yahoo Finance.
    Yêu cầu thêm hậu tố .VN cho thị trường Việt Nam.
    """
    symbol = f"{ticker}.VN"
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        
        # Yahoo Finance trả về một dictionary (info) chứa hàng trăm trường dữ liệu
        # Ta chủ động trích xuất các chỉ số quan trọng nhất
        ratios = {
            "P/E": info.get("trailingPE", "N/A"),
            "P/B": info.get("priceToBook", "N/A"),
            "ROE": info.get("returnOnEquity", "N/A"),
            "ROA": info.get("returnOnAssets", "N/A"),
            "Biên LN Gộp": info.get("grossMargins", "N/A"),
            "Biên LN Ròng": info.get("profitMargins", "N/A"),
            "Vốn hóa (Tỷ)": info.get("marketCap", 0) / 1e9 if info.get("marketCap") else "N/A"
        }
        
        # Bọc vào list để tạo DataFrame 1 dòng
        return pd.DataFrame([ratios])
    except Exception as e:
        print(f"Lỗi yfinance (Ratios) - Mã {ticker}: {e}")
        return pd.DataFrame()

def fetch_income_statement(ticker: str, is_yearly: bool = False) -> pd.DataFrame:
    """
    Kéo Báo cáo kết quả kinh doanh từ Yahoo Finance.
    """
    symbol = f"{ticker}.VN"
    try:
        stock = yf.Ticker(symbol)
        
        # .financials trả về BCTC năm, .quarterly_financials trả về BCTC quý
        if is_yearly:
            df = stock.financials
        else:
            df = stock.quarterly_financials
            
        if df is not None and not df.empty:
            # Yahoo Finance trả về bảng với các khoản mục là Hàng (Index), Thời gian là Cột
            return df
    except Exception as e:
        print(f"Lỗi yfinance (Income) - Mã {ticker}: {e}")
        
    return pd.DataFrame()
