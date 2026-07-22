# 2_📈_Advanced_Chart.py module
# pages/2_📈_Advanced_Chart.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
import plotly.graph_objects as go

# Thiết lập đường dẫn để import được các module từ thư mục cha
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.dnse_client import fetch_historical_data
from core.indicators import calculate_sma
from ui.charts import create_price_volume_chart

# Tối ưu hóa: Cache dữ liệu để tránh gọi API liên tục khi người dùng đổi loại biểu đồ
@st.cache_data(ttl=300) # Cache sống trong 5 phút (300 giây)
def load_and_cache_data(ticker: str, start: int, end: int) -> pd.DataFrame:
    """Gọi API thông qua data layer và lưu cache."""
    return fetch_historical_data(ticker, start, end)

def render_advanced_chart():
    """Hàm render giao diện chính của trang Biểu đồ."""
    
    st.title("📈 Biểu Đồ Kỹ Thuật Nâng Cao")
    
    # Lấy ticker từ trạng thái toàn cục, nếu không có thì mặc định là VPH
    ticker = st.session_state.get('current_ticker', 'VPH')
    st.subheader(f"Phân tích hành vi giá - Mã: {ticker}")
    
    # --- KHU VỰC ĐIỀU KHIỂN (CONTROLS) ---
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Thay vì dùng dropdown cứng nhắc, ta cho chọn số ngày linh hoạt
        days_back = st.selectbox("Khung thời gian (Ngày):", [30, 90, 180, 365, 730], index=1)
        
    with col2:
        # Cho phép tinh chỉnh chu kỳ SMA trực tiếp thay vì hardcode 50 ngày
        sma_window = st.number_input("Chu kỳ SMA:", min_value=5, max_value=200, value=50, step=5)
        
    with col3:
        plot_type = st.selectbox("Loại biểu đồ:", ['Candle', 'Line'])
        
    # --- XỬ LÝ THỜI GIAN VÀ GỌI DATA ---
    end_time = int(datetime.now().timestamp())
    start_time = int((datetime.now() - timedelta(days=days_back)).timestamp())
    
    with st.spinner(f'Đang đồng bộ dữ liệu {ticker} từ DNSE...'):
        df = load_and_cache_data(ticker, start_time, end_time)
        
    if df.empty:
        st.warning("Không có dữ liệu cho khoảng thời gian này hoặc kết nối API bị lỗi.")
        return
        
    # --- XỬ LÝ LOGIC ĐỊNH LƯỢNG ---
    df['SMA'] = calculate_sma(df, window=sma_window)
    
    # --- RENDER BIỂU ĐỒ ---
    # 1. Gọi hàm tạo khung biểu đồ cơ sở từ UI component
    fig = create_price_volume_chart(df, ticker, plot_type)
    
    # 2. Add thêm đường SMA lên trục Y chính (secondary_y=False)
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df['SMA'], 
            mode='lines', 
            name=f'SMA {sma_window}', 
            line=dict(color='orange', width=1.5)
        ),
        secondary_y=False
    )
    
    # 3. Hiển thị lên Streamlit, cho phép mở rộng full width
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    render_advanced_chart()