# pages/7_🧪_Alpha_Backtest.py
import streamlit as st
import plotly.graph_objects as go
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data.mock_data import get_mock_stock_data
from core.alpha_engine import AlphaEngine

def render_alpha_page():
    st.title("🧪 Alpha Expression Backtesting Engine")
    st.markdown("Môi trường kiểm thử tín hiệu Alpha toán học theo tiêu chuẩn WorldQuant/Citadel.")

    # Sidebar Controls
    st.sidebar.header("Cấu hình Backtest")
    ticker = st.sidebar.text_input("Mã cổ phiếu", value="VNM").upper()
    alpha_choice = st.sidebar.selectbox(
        "Mô hình Alpha Tín hiệu",
        ["Momentum_RSI", "Mean_Reversion_ZScore", "Volume_Price_Trend"]
    )
    initial_capital = st.sidebar.number_input("Vốn ban đầu (VND)", value=100000000, step=10000000)

    # Fetch Data
    df = get_mock_stock_data(ticker)
    
    # Run Alpha Engine
    signal = AlphaEngine.calculate_alpha_signal(df, expression_type=alpha_choice)
    results = AlphaEngine.backtest_signal(df, signal, initial_capital=initial_capital)
    
    res_df = results['data']

    # KPIs Row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Tổng Lợi Nhuận", f"{results['total_return']*100:.2f}%")
    col2.metric("Sharpe Ratio", f"{results['sharpe_ratio']:.2f}")
    col3.metric("Max Drawdown", f"{results['max_drawdown']*100:.2f}%")
    col4.metric("Tỷ Lệ Thắng (Win Rate)", f"{results['win_rate']*100:.2f}%")

    # Interactive Chart (Equity Curve vs Benchmark)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=res_df.index, y=res_df['equity'], name='Chiến lược Alpha', line=dict(color='#00CC96', width=2)))
    fig.add_trace(go.Scatter(x=res_df.index, y=initial_capital * res_df['cum_market_return'], name='Benchmark (Buy & Hold)', line=dict(color='#636EFA', dash='dash')))
    
    fig.update_layout(
        title=f"Đường Cong Tài Sản (Equity Curve) - {ticker} ({alpha_choice})",
        xaxis_title="Ngày",
        yaxis_title="Giá trị Tài sản (VND)",
        template="plotly_white",
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    render_alpha_page()
    