# pages/4_⚖️_Risk_Analytics.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import statsmodels.api as sm
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data.dnse_client import fetch_historical_data
from core.quantitative import run_monte_carlo

@st.cache_data(ttl=300)
def load_and_calc_returns(ticker: str, days: int, is_index: bool = False) -> pd.Series:
    """Lấy dữ liệu qua module dnse_client và tính log return siêu tốc."""
    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=days)).timestamp())
    df = fetch_historical_data(ticker, start_ts, end_ts, is_index=is_index)
    if not df.empty:
        return np.log(df['Close'] / df['Close'].shift(1)).dropna().rename(ticker)
    return pd.Series(dtype=float, name=ticker)

def render_monte_carlo_page():
    if 'ticker' not in st.session_state:
        st.session_state['ticker'] = 'VCB'
    current_ticker = st.session_state['ticker']

    st.sidebar.markdown("### ⚙️ Bảng Điều Khiển")
    
    # Xử lý input an toàn, chống lỗi lề
    input_ticker = st.sidebar.text_input("Mã cổ phiếu:", value=current_ticker, key="mc_ticker").upper()
    if input_ticker and input_ticker != current_ticker:
        st.session_state['ticker'] = input_ticker
        st.rerun()

    st.markdown("""
        <style>
        .terminal-header {
            font-family: 'Courier New', Courier, monospace;
            color: #ff9900;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f'<h1 class="terminal-header">⚖️ Phân Tích Rủi Ro & Định Giá: {current_ticker}</h1>', unsafe_allow_html=True)
    st.caption("Tích hợp đo lường rủi ro hệ thống qua mô hình CAPM và dự phóng rủi ro đuôi (Tail Risk - VaR) bằng phương pháp mô phỏng ngẫu nhiên Monte Carlo.")
    
    tab_mc, tab_capm = st.tabs(["🎲 Mô Phỏng Monte Carlo", "📐 Mô Hình CAPM"])

    with tab_mc:
        c1, c2 = st.columns(2)
        sims = c1.selectbox("Kịch bản (n):", [200, 500, 1000], index=1)
        horizon = c2.selectbox("Khung thời gian (ngày):", [30, 60, 90, 252], index=0)
        
        with st.spinner("Đang tính toán ma trận..."):
            end_ts = int(datetime.now().timestamp())
            start_ts = int((datetime.now() - timedelta(days=365)).timestamp())
            hist_df = fetch_historical_data(current_ticker, start_ts, end_ts)
            
            if not hist_df.empty:
                current_price = hist_df['Close'].iloc[-1]
                sim_df = run_monte_carlo(hist_df['Close'], horizon, sims)
                end_prices = sim_df.iloc[-1, :]
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Giá hiện tại", f"{current_price:,.2f}")
                m2.metric("Kỳ vọng", f"{end_prices.mean():,.2f}")
                m3.metric("VaR 95%", f"{np.percentile(end_prices, 5):,.2f}", delta_color="inverse")

                fig = px.line(sim_df.sample(n=min(sims, 100), axis=1), template="plotly_dark")
                fig.update_layout(showlegend=False, xaxis_title="Ngày", yaxis_title="Giá")
                st.plotly_chart(fig, width='stretch')

    with tab_capm:
        st.subheader("Capital Asset Pricing Model (CAPM)")
        with st.spinner("Đang chạy hồi quy OLS..."):
            stock_ret = load_and_calc_returns(current_ticker, 365)
            market_ret = load_and_calc_returns('VNINDEX', 365, is_index=True)
            
            if not stock_ret.empty and not market_ret.empty:
                data = pd.concat([stock_ret, market_ret], axis=1, join='inner')
                rf = 0.045 / 252
                Y = data[current_ticker] - rf
                X = sm.add_constant(data['VNINDEX'] - rf)
                model = sm.OLS(Y, X).fit()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Beta (Rủi ro)", f"{model.params['VNINDEX']:.4f}")
                c2.metric("Alpha", f"{model.params['const']:.6f}")
                c3.metric("R-squared", f"{model.rsquared*100:.2f}%")
                
                fig = px.scatter(data, x='VNINDEX', y=current_ticker, trendline='ols', template="plotly_dark")
                st.plotly_chart(fig, width='stretch')

if __name__ == "__main__":
    render_monte_carlo_page()
    