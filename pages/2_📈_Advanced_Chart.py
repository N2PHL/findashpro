# pages/2_📈_Advanced_Chart.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
import plotly.graph_objects as go

# Cấu hình đường dẫn tuyệt đối để import từ thư mục cha
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.dnse_client import fetch_historical_data
from core.indicators import calculate_sma
from ui.charts import create_price_volume_chart

# Tối ưu hóa: Cache dữ liệu để tránh gọi API liên tục khi người dùng đổi loại biểu đồ
@st.cache_data(ttl=300)
def load_and_cache_data(ticker: str, start: int, end: int) -> pd.DataFrame:
    """Gọi API thông qua data layer và lưu cache."""
    return fetch_historical_data(ticker, start, end)

def render_advanced_chart():
    # --- 1. QUẢN LÝ TRẠNG THÁI (SESSION STATE) ---
    if 'ticker' not in st.session_state:
        st.session_state['ticker'] = 'VCB'

    # --- 2. SIDEBAR ĐỒNG BỘ ---
    st.sidebar.markdown("### ⚙️ Bảng Điều Khiển")
    st.sidebar.divider()
    
    input_ticker = st.sidebar.text_input(
        "Nhập mã cổ phiếu (Ticker):", 
        value=st.session_state['ticker'],
        key="advanced_chart_ticker_input" # Đảm bảo key không trùng lặp với trang khác
    ).upper()
    
    if input_ticker != st.session_state['ticker']:
        st.session_state['ticker'] = input_ticker
        st.rerun()

    current_ticker = st.session_state['ticker']

    # --- 3. GIAO DIỆN CHÍNH (UI COMMAND CENTER) ---
    st.markdown("""
        <style>
        .terminal-header {
            font-family: 'Courier New', Courier, monospace;
            color: #ff9900;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f'<h1 class="terminal-header">📈 Biểu Đồ Kỹ Thuật: {current_ticker}</h1>', unsafe_allow_html=True)
    st.caption("Phân tích hành vi giá (Price Action) và động lượng thanh khoản với đa khung thời gian.")
    
    # --- 4. KHU VỰC ĐIỀU KHIỂN (CONTROLS) ---
    with st.container(border=True):
        st.markdown("**Tùy chỉnh thông số**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            days_back = st.selectbox("Khung thời gian (Ngày):", [30, 90, 180, 365, 730], index=1)
            
        with col2:
            sma_window = st.number_input("Chu kỳ SMA:", min_value=5, max_value=200, value=50, step=5)
            
        with col3:
            plot_type = st.selectbox("Loại biểu đồ:", ['Candle', 'Line'])
            
    # --- 5. XỬ LÝ THỜI GIAN VÀ GỌI DATA ---
    end_time = int(datetime.now().timestamp())
    start_time = int((datetime.now() - timedelta(days=days_back)).timestamp())
    
    with st.spinner(f'Đang trích xuất dữ liệu giá cho mã {current_ticker}...'):
        df = load_and_cache_data(current_ticker, start_time, end_time)
        
    if df.empty:
        st.warning("Không có dữ liệu cho khoảng thời gian này hoặc kết nối API bị lỗi.")
        return
        
    # --- 6. XỬ LÝ LOGIC ĐỊNH LƯỢNG ---
    df['SMA'] = calculate_sma(df, window=sma_window)
    
    # --- 7. RENDER BIỂU ĐỒ ---
    # Gọi hàm tạo khung biểu đồ cơ sở từ UI component
    fig = create_price_volume_chart(df, current_ticker, plot_type)
    
    # Add thêm đường SMA lên trục Y chính (secondary_y=False)
    fig.add_trace(
        go.Scatter(
            x=df.index, 
            y=df['SMA'], 
            mode='lines', 
            name=f'SMA {sma_window}', 
            line=dict(color='#ff9900', width=1.5) # Màu cam Bloomberg
        ),
        secondary_y=False
    )
    
    # Ép chuẩn giao diện Dark Mode cho Plotly để đồng bộ với ứng dụng
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Hiển thị lên Streamlit, mở rộng full width
    st.plotly_chart(fig, width='stretch')

if __name__ == "__main__":
    render_advanced_chart()
