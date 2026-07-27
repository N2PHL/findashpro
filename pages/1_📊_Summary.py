# 1_📊_Summary.py module
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
    """Hàm render giao diện trang Tổng quan."""
    st.title("📊 Tổng Quan Cổ Phiếu")
    
    # Lấy ticker từ session state (đã được cấu hình ở Sidebar trong app.py)
    ticker = st.session_state.get('current_ticker', 'VPH')
    
    with st.spinner(f"Đang đồng bộ dữ liệu tổng quan cho mã {ticker}..."):
        df = load_summary_data(ticker)
        
    if df.empty:
        st.warning("Không có dữ liệu cho mã cổ phiếu này.")
        return

    # --- CORE LOGIC: TÍNH TOÁN KPI ---
    # Lấy giá trị của ngày giao dịch gần nhất (dòng cuối cùng) và ngày trước đó
    current_price = df['Close'].iloc[-1]
    prev_price = df['Close'].iloc[-2]
    
    # Tính mức thay đổi giá và phần trăm thay đổi
    price_change = current_price - prev_price
    pct_change = (price_change / prev_price) * 100
    
    # Tìm đỉnh và đáy trong 1 năm (52 tuần)
    high_52w = df['High'].max()
    low_52w = df['Low'].min()
    
    # Đánh giá thanh khoản (Khối lượng hôm nay so với trung bình 20 phiên)
    current_vol = df['Volume'].iloc[-1]
    avg_vol_20d = df['Volume'].tail(20).mean()
    vol_pct_change = ((current_vol - avg_vol_20d) / avg_vol_20d) * 100

    # --- RENDER GIAO DIỆN ---
    st.subheader(f"Chỉ số Giao dịch - {ticker}")
    
    # Chia 4 cột để hiển thị KPI Cards
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

    st.markdown("---")
    st.subheader("Diễn biến giá 30 ngày gần nhất")
    
    # --- RENDER BIỂU ĐỒ AREA (SPARKLINE STYLE) ---
    # Cắt lấy 30 dòng cuối cùng để vẽ đồ thị ngắn hạn
    df_30d = df.tail(30)
    
    # Dùng Plotly Express vẽ Area Chart nhanh gọn
    fig = px.area(
        df_30d, 
        x=df_30d.index, 
        y='Close', 
        color_discrete_sequence=['#00b4d8'] # Màu xanh lam hiện đại
    )
    
    # Tối ưu layout để đồ thị không chiếm quá nhiều diện tích
    fig.update_layout(
        xaxis_title="", 
        yaxis_title="Giá đóng cửa",
        height=350,
        margin=dict(l=0, r=0, t=10, b=0),
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, width="stretch")

if __name__ == "__main__":
    render_summary_page()