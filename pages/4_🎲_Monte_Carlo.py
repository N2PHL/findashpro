# 4_🎲_Monte_Carlo.py module
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
    st.title("🎲 Mô Phỏng Monte Carlo & Value at Risk (VaR)")
    
    ticker = st.session_state.get('current_ticker', 'VPH')
    st.markdown(f"Dự phóng hành vi giá tương lai cho mã **{ticker}** dựa trên phương sai lịch sử.")
    
    # --- KHU VỰC ĐIỀU KHIỂN ---
    col1, col2 = st.columns(2)
    with col1:
        simulations = st.selectbox("Số lượng kịch bản mô phỏng (n):", [200, 500, 1000, 5000], index=1)
    with col2:
        time_horizon = st.selectbox("Khung thời gian dự phóng (ngày):", [30, 60, 90, 252], index=0)
        
    # --- CHUẨN BỊ DỮ LIỆU ĐẦU VÀO ---
    # Lấy dữ liệu 1 năm (365 ngày) gần nhất để tính độ lệch chuẩn (Volatility) cho chuẩn xác
    with st.spinner("Đang tính toán ma trận ngẫu nhiên..."):
        historical_df = load_historical_data(ticker, days=365)
        
        if historical_df.empty:
            st.error("Không đủ dữ liệu lịch sử để chạy mô phỏng.")
            return
            
        close_prices = historical_df['Close']
        current_price = close_prices.iloc[-1]
        
        # --- CHẠY CORE LOGIC ---
        simulation_df = run_monte_carlo(close_prices, time_horizon, simulations)
        
    # --- TÍNH TOÁN METRICS (KPIs) ---
    # Lấy mảng giá của ngày cuối cùng trong tất cả các kịch bản
    ending_prices = simulation_df.iloc[-1, :]
    
    # Tính Value at Risk (VaR) ở mức tin cậy 95% (percentile thứ 5)
    var_95_price = np.percentile(ending_prices, 5)
    var_value = current_price - var_95_price
    expected_price = ending_prices.mean()
    
    # Hiển thị Metric Cards trực quan
    st.markdown("### 📊 Chỉ số Rủi ro & Kỳ vọng")
    m1, m2, m3 = st.columns(3)
        # Chuyển định dạng từ .0f (không thập phân) sang .2f (lấy 2 chữ số thập phân)
    m1.metric("Giá hiện tại", f"{current_price:,.2f}")
    m2.metric("Giá kỳ vọng (Trung bình)", f"{expected_price:,.2f}", f"{(expected_price - current_price):,.2f}")
    m3.metric("VaR 95% (Mức rủi ro tối đa)", f"{var_95_price:,.2f}", f"-{var_value:,.2f}", delta_color="inverse")

    # --- RENDER BIỂU ĐỒ 1: CÁC KỊCH BẢN ĐƯỜNG GIÁ ---
    st.markdown("### 📈 Biểu đồ các kịch bản (Price Paths)")
    
    fig_paths = go.Figure()
    
    # TỐI ƯU HÓA GIAO DIỆN: Chỉ vẽ ngẫu nhiên tối đa 100 đường để web không bị lag,
    # nhưng tính toán VaR vẫn dựa trên toàn bộ 1000/5000 kịch bản.
    sample_size = min(simulations, 100)
    sampled_columns = np.random.choice(simulation_df.columns, size=sample_size, replace=False)
    
    for col in sampled_columns:
        fig_paths.add_trace(
            go.Scatter(
                x=simulation_df.index, 
                y=simulation_df[col], 
                mode='lines', 
                line=dict(width=1, color='rgba(150, 150, 150, 0.2)'), # Màu xám trong suốt
                showlegend=False,
                hoverinfo='skip' # Tắt tooltip cho các đường này để tăng tốc render
            )
        )
    
    # Vẽ đè một đường ngang thể hiện giá hiện tại
    fig_paths.add_hline(y=current_price, line_dash="dash", line_color="red", annotation_text="Giá hiện tại")
    
    fig_paths.update_layout(
        height=500, 
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis_title="Ngày dự phóng (t)",
        yaxis_title="Mức Giá"
    )
    st.plotly_chart(fig_paths, width="stretch")

    # --- RENDER BIỂU ĐỒ 2: PHÂN PHỐI XÁC SUẤT GIÁ KẾT THÚC ---
    st.markdown("### 📉 Phân phối Xác suất & Mức cắt lỗ (VaR)")
    
    fig_dist = px.histogram(
        ending_prices, 
        nbins=50, 
        title=f"Phân phối Giá sau {time_horizon} ngày",
        color_discrete_sequence=['#4C78A8']
    )
    
    # Vẽ mốc VaR 95%
    fig_dist.add_vline(
        x=var_95_price, 
        line_dash="dot", 
        line_color="red", 
        annotation_text=f"VaR 95%: {var_95_price:,.0f}"
    )
    
    fig_dist.update_layout(showlegend=False, xaxis_title="Giá kết thúc", yaxis_title="Tần suất")
    st.plotly_chart(fig_dist, width="stretch")

if __name__ == "__main__":
    render_monte_carlo_page()