# pages/4_🎲_Monte_Carlo.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os

# Cấu hình đường dẫn tuyệt đối
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.dnse_client import fetch_historical_data
from core.quantitative import run_monte_carlo

@st.cache_data(ttl=300)
def load_historical_data(ticker: str, days: int) -> pd.DataFrame:
    """Lấy dữ liệu lịch sử để làm cơ sở tính toán biến động (volatility)."""
    end_time = int(datetime.now().timestamp())
    start_time = int((datetime.now() - timedelta(days=days)).timestamp())
    return fetch_historical_data(ticker, start_time, end_time)

def render_monte_carlo_page():
    # --- 1. QUẢN LÝ TRẠNG THÁI (SESSION STATE) ---
    if 'ticker' not in st.session_state:
        st.session_state['ticker'] = 'VCB'

    # --- 2. SIDEBAR ĐỒNG BỘ ---
    st.sidebar.markdown("### ⚙️ Bảng Điều Khiển")
    st.sidebar.divider()
    
    input_ticker = st.sidebar.text_input(
        "Nhập mã cổ phiếu (Ticker):", 
        value=st.session_state['ticker'],
        key="monte_carlo_ticker_input" # Key duy nhất cho trang này
    ).upper()
    
    if input_ticker != st.session_state['ticker']:
        st.session_state['ticker'] = input_ticker
        st.rerun()

    current_ticker = st.session_state['ticker']

    # --- 3. GIAO DIỆN CHÍNH (COMMAND CENTER) ---
    st.markdown("""
        <style>
        .terminal-header {
            font-family: 'Courier New', Courier, monospace;
            color: #ff9900;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f'<h1 class="terminal-header">🎲 Mô Phỏng Monte Carlo: {current_ticker}</h1>', unsafe_allow_html=True)
    st.caption("Dự phóng hành vi giá tương lai và đo lường rủi ro (VaR) dựa trên phương sai lịch sử.")
    
    # --- 4. KHU VỰC ĐIỀU KHIỂN ---
    with st.container(border=True):
        st.markdown("**Cấu hình thuật toán**")
        col1, col2 = st.columns(2)
        with col1:
            simulations = st.selectbox("Số lượng kịch bản (n):", [200, 500, 1000, 5000], index=1)
        with col2:
            time_horizon = st.selectbox("Khung thời gian dự phóng (ngày):", [30, 60, 90, 252], index=0)
        
    # --- 5. CHUẨN BỊ DỮ LIỆU ĐẦU VÀO ---
    with st.spinner(f"Đang tính toán ma trận ngẫu nhiên cho mã {current_ticker}..."):
        historical_df = load_historical_data(current_ticker, days=365)
        
        if historical_df.empty:
            st.error("Không đủ dữ liệu lịch sử để chạy mô phỏng.")
            return
            
        close_prices = historical_df['Close']
        current_price = close_prices.iloc[-1]
        
        # --- CHẠY CORE LOGIC ---
        simulation_df = run_monte_carlo(close_prices, time_horizon, simulations)
        
    # --- 6. TÍNH TOÁN METRICS (KPIs) ---
    ending_prices = simulation_df.iloc[-1, :]
    
    # Tính Value at Risk (VaR) ở mức tin cậy 95%
    var_95_price = np.percentile(ending_prices, 5)
    var_value = current_price - var_95_price
    expected_price = ending_prices.mean()
    
    st.markdown("### 📊 Chỉ số Rủi ro & Kỳ vọng")
    with st.container(border=True):
        m1, m2, m3 = st.columns(3)
        m1.metric("Giá hiện tại", f"{current_price:,.2f}")
        m2.metric("Giá kỳ vọng (Trung bình)", f"{expected_price:,.2f}", f"{(expected_price - current_price):,.2f}")
        m3.metric("VaR 95% (Rủi ro tối đa)", f"{var_95_price:,.2f}", f"-{var_value:,.2f}", delta_color="inverse")

    st.divider()

    # --- 7. RENDER BIỂU ĐỒ KỊCH BẢN GIÁ ---
    st.markdown("### 📈 Phân mảnh các kịch bản (Price Paths)")
    
    fig_paths = go.Figure()
    
    # Render tối đa 100 đường để đảm bảo FPS mượt mà
    sample_size = min(simulations, 100)
    sampled_columns = np.random.choice(simulation_df.columns, size=sample_size, replace=False)
    
    for col in sampled_columns:
        fig_paths.add_trace(
            go.Scatter(
                x=simulation_df.index, 
                y=simulation_df[col], 
                mode='lines', 
                line=dict(width=1, color='rgba(100, 149, 237, 0.15)'), # Xanh lam trong suốt hợp với Dark Mode
                showlegend=False,
                hoverinfo='skip'
            )
        )
    
    # Đường giá hiện tại
    fig_paths.add_hline(y=current_price, line_dash="dash", line_color="#ff9900", annotation_text="Giá hiện tại")
    
    fig_paths.update_layout(
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=500, 
        margin=dict(l=0, r=0, t=20, b=0),
        xaxis_title="Ngày dự phóng (t)",
        yaxis_title="Mức Giá"
    )
    st.plotly_chart(fig_paths, width='stretch')

    # --- 8. RENDER BIỂU ĐỒ PHÂN PHỐI TẦN SUẤT ---
    st.markdown("### 📉 Phân phối Xác suất & Mức cắt lỗ (VaR)")
    
    fig_dist = px.histogram(
        ending_prices, 
        nbins=50, 
        color_discrete_sequence=['#1E88E5'],
        template="plotly_dark"
    )
    
    fig_dist.add_vline(
        x=var_95_price, 
        line_dash="dot", 
        line_color="#D32F2F", 
        annotation_text=f"VaR 95%: {var_95_price:,.2f}"
    )
    
    fig_dist.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False, 
        xaxis_title="Mức giá kết thúc (Terminal Price)", 
        yaxis_title="Tần suất (Số kịch bản)",
        margin=dict(l=0, r=0, t=20, b=0)
    )
    st.plotly_chart(fig_dist, width='stretch')

if __name__ == "__main__":
    render_monte_carlo_page()
