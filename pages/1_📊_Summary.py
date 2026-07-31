# pages/1_📊_Summary.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os

# Cấu hình đường dẫn tuyệt đối để import từ thư mục cha
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.dnse_client import fetch_historical_data

@st.cache_data(ttl=300)
def load_summary_data(ticker: str) -> pd.DataFrame:
    """
    Lấy dữ liệu 1 năm (365 ngày) để tính toán các chỉ số cơ bản như Đỉnh/Đáy 52 tuần.
    """
    end_time = int(datetime.now().timestamp())
    start_time = int((datetime.now() - timedelta(days=365)).timestamp())
    return fetch_historical_data(ticker, start_time, end_time)

def render_summary_page():
    # --- 1. QUẢN LÝ TRẠNG THÁI (SESSION STATE) ---
    # Khởi tạo giá trị mặc định nếu người dùng truy cập trực tiếp vào trang này
    if 'ticker' not in st.session_state:
        st.session_state['ticker'] = 'VCB'

    # --- 2. SIDEBAR ĐỒNG BỘ ---
    st.sidebar.markdown("### ⚙️ Bảng Điều Khiển")
    st.sidebar.divider()
    
    # Ô nhập mã cổ phiếu được liên kết chặt chẽ với Session State
    input_ticker = st.sidebar.text_input(
        "Nhập mã cổ phiếu (Ticker):", 
        value=st.session_state['ticker'],
        key="summary_ticker_input" # Đặt key để tránh xung đột id nội bộ của Streamlit
    ).upper()
    
    # Kích hoạt làm mới toàn bộ luồng dữ liệu nếu phát hiện mã mới
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

    st.markdown(f'<h1 class="terminal-header">📊 Tổng Quan Giao Dịch: {current_ticker}</h1>', unsafe_allow_html=True)
    st.caption("Tổng hợp biến động giá, thanh khoản và các mốc định vị giá trị trong 52 tuần.")
    
    with st.spinner(f"Đang đồng bộ dữ liệu thị trường cho mã {current_ticker}..."):
        df = load_summary_data(current_ticker)
        
    if df.empty:
        st.warning(f"Không tìm thấy dữ liệu giao dịch cho mã {current_ticker} trên hệ thống.")
        return

    # --- 4. CORE LOGIC: TÍNH TOÁN KPI ---
    current_price = df['Close'].iloc[-1]
    prev_price = df['Close'].iloc[-2]
    
    price_change = current_price - prev_price
    pct_change = (price_change / prev_price) * 100
    
    high_52w = df['High'].max()
    low_52w = df['Low'].min()
    
    current_vol = df['Volume'].iloc[-1]
    avg_vol_20d = df['Volume'].tail(20).mean()
    vol_pct_change = ((current_vol - avg_vol_20d) / avg_vol_20d) * 100

    # --- 5. RENDER BẢNG ĐIỀU KHIỂN KPI ---
    st.markdown("### Chỉ Số Real-time")
    
    # Sử dụng container có viền để làm nổi bật khu vực số liệu
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            st.metric(
                label="Giá hiện tại", 
                value=f"{current_price:,.2f}", 
                delta=f"{price_change:,.2f} ({pct_change:.2f}%)"
            )
        with c2:
            st.metric(
                label="Khối lượng GD", 
                value=f"{current_vol:,.0f}", 
                delta=f"{vol_pct_change:.1f}% vs 20D Avg"
            )
        with c3:
            st.metric(
                label="Đỉnh 52 Tuần", 
                value=f"{high_52w:,.2f}"
            )
        with c4:
            st.metric(
                label="Đáy 52 Tuần", 
                value=f"{low_52w:,.2f}"
            )

    st.divider()

    # --- 6. RENDER BIỂU ĐỒ AREA (SPARKLINE STYLE) ---
    st.markdown("### Diễn biến giá 30 ngày gần nhất")
    
    df_30d = df.tail(30)
    
    # Thiết lập biểu đồ tương thích Dark Mode
    fig = px.area(
        df_30d, 
        x=df_30d.index, 
        y='Close', 
        color_discrete_sequence=['#1E88E5'], # Xanh lam đậm đặc trưng của Terminal
        template="plotly_dark" # Ép biểu đồ theo tông màu tối
    )
    
    fig.update_layout(
        xaxis_title="", 
        yaxis_title="Giá đóng cửa",
        height=400,
        margin=dict(l=0, r=0, t=20, b=0),
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    
    st.plotly_chart(fig, width='stretch')

if __name__ == "__main__":
    render_summary_page()


