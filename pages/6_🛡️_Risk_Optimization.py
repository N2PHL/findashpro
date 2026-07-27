# pages/6_🛡️_Risk_Optimization.py
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import sys
import os
from datetime import datetime, timedelta
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data.dnse_client import fetch_historical_data
from core.portfolio_opt import PortfolioOptimizer

def render_risk_page():
    st.title("🛡️ Dynamic Efficient Frontier & Risk Stress Testing")
    st.markdown("Tối ưu hóa danh mục theo mô hình Markowitz và Đánh giá rủi ro thiên tai (Value at Risk - VaR).")

    st.sidebar.header("Cấu hình Danh mục")
    
    # 1. Ô nhập liệu cho phép gõ nhiều mã, cách nhau bằng dấu phẩy
    ticker_input = st.sidebar.text_input(
        "Nhập rổ cổ phiếu (cách nhau bằng dấu phẩy):", 
        value="VNM, VIC, HPG, FPT"
    )
    
    # 2. Xử lý chuỗi nhập vào: tách bằng dấu phẩy, xóa khoảng trắng và viết hoa
    tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]
    
    # Báo lỗi nếu người dùng không nhập mã nào hoặc nhập ít hơn 2 mã (không thể tối ưu ma trận)
    if len(tickers) < 2:
        st.error("Vui lòng nhập ít nhất 2 mã cổ phiếu để tối ưu hóa danh mục.")
        st.stop() # Dừng chạy code bên dưới cho đến khi nhập đủ

    capital = st.sidebar.number_input("Tổng vốn đầu tư (VND)", value=500000000, step=50000000)
     # Xác định khung thời gian 1 năm cho ma trận rủi ro
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    start_ts = int(start_date.timestamp())
    end_ts = int(end_date.timestamp())

    # Thu thập dữ liệu biến động giá và chuẩn hóa cột
    price_dict = {}
    for t in tickers:
        df_temp = fetch_historical_data(t, start_ts, end_ts)
        
        # Chuẩn hóa tên cột về chữ thường
        df_temp.columns = df_temp.columns.str.lower()
        # Xử lý trường hợp viết tắt
        df_temp = df_temp.rename(columns={'c': 'close'})
        
        # Lưu vào dictionary
        price_dict[t] = df_temp['close']
        
    df_prices = pd.DataFrame(price_dict)
    returns_df = df_prices.pct_change().dropna()

    mean_returns = returns_df.mean()
    cov_matrix = returns_df.cov()

    # 1. Tối ưu hóa Tỷ trọng
    opt_weights = PortfolioOptimizer.optimize_sharpe(mean_returns, cov_matrix)
    opt_ret, opt_std, opt_sharpe = PortfolioOptimizer.calculate_performance(opt_weights, mean_returns, cov_matrix)

    # 2. Tính toán Lợi nhuận danh mục tối ưu
    portfolio_returns = (returns_df * opt_weights).sum(axis=1)
    var_metrics = PortfolioOptimizer.calculate_var_cvar(portfolio_returns, confidence_level=0.95, capital=capital)

    # Hiển thị kết quả tối ưu
    st.subheader("1. Tỷ Trọng Tối Ưu (Max Sharpe Portfolio)")
    cols = st.columns(len(tickers))
    for i, t in enumerate(tickers):
        cols[i].metric(label=f"Mã {t}", value=f"{opt_weights[i]*100:.1f}%")

    # Hiển thị Đánh giá Rủi ro VaR/CVaR
    st.subheader("2. Kiểm Thử Rủi Ro (Stress Testing - 95% Confidence)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Sharpe Ratio Tối Ưu", f"{opt_sharpe:.2f}")
    c2.metric("Value at Risk (VaR 1 Ngày)", f"-{var_metrics['var_amount']/1_000_000:,.2f} Tr VNĐ", f"-{var_metrics['var_pct']*100:.2f}%")
    c3.metric("Conditional VaR (CVaR 1 Ngày)", f"-{var_metrics['cvar_amount']/1_000_000:,.2f} Tr VNĐ", f"-{var_metrics['cvar_pct']*100:.2f}%")

    # 3. Vẽ biểu đồ Efficient Frontier
    st.subheader("3. Biểu Đồ Đường Biên Hiệu Quả (Efficient Frontier)")
    ef_results = PortfolioOptimizer.generate_efficient_frontier(mean_returns, cov_matrix)

    fig = go.Figure()
       # Các danh mục ngẫu nhiên
    fig.add_trace(go.Scatter(
        x=ef_results[0, :], y=ef_results[1, :],
        mode='markers',
        marker=dict(
            color=ef_results[2, :], 
            colorscale='Viridis', 
            showscale=True, 
            size=5, 
            colorbar=dict(title="Sharpe")  # <-- Đã sửa tại đây
        ),
        name="Mô phỏng Danh mục"
    ))
    # Điểm tối ưu Max Sharpe
    fig.add_trace(go.Scatter(
        x=[opt_std], y=[opt_ret],
        mode='markers',
        marker=dict(color='Red', size=15, symbol='star'),
        name="Max Sharpe Ratio"
    ))

    fig.update_layout(
        xaxis_title="Độ lệch chuẩn / Rủi ro hàng năm (Volatility)",
        yaxis_title="Lợi nhuận kỳ vọng hàng năm (Expected Return)",
        template="plotly_white",
        height=500
    )
    st.plotly_chart(fig, width="stretch")

if __name__ == "__main__":
    render_risk_page()
