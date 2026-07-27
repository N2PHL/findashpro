# 5_💼_Portfolio.py module
# pages/5_💼_Portfolio.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os

# Thiết lập đường dẫn absolute để import module từ thư mục root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.dnse_client import fetch_historical_data

@st.cache_data(ttl=300)
def load_multiple_tickers(tickers: list, days: int) -> pd.DataFrame:
    """Gọi API lấy dữ liệu đóng cửa của nhiều mã cổ phiếu và gộp thành một DataFrame."""
    end_time = int(datetime.now().timestamp())
    start_time = int((datetime.now() - timedelta(days=days)).timestamp())
    
    df_combined = pd.DataFrame()
    for ticker in tickers:
        df = fetch_historical_data(ticker, start_time, end_time)
        if not df.empty:
            # Chỉ lấy cột Close Price, ghép vào DataFrame tổng với tên cột là mã ticker
            df_combined[ticker] = df['Close']
            
    # Loại bỏ các dòng bị khuyết dữ liệu do lệch ngày giao dịch
    return df_combined.dropna()

def render_portfolio_page():
    st.title("💼 Xu Hướng Danh Mục Đầu Tư")
    st.markdown("So sánh hiệu suất sinh lời và xu hướng giá của rổ cổ phiếu trong cùng một khoảng thời gian.")
    
    # --- KHU VỰC ĐIỀU KHIỂN ---
    col1, col2 = st.columns([3, 1])
    with col1:
        # Multiselect cho phép chọn nhiều mã
        default_tickers = ['NVL', 'OCB', 'STK', 'VPH', 'TIP']
        available_options = ['FPT', 'VCB', 'VHM', 'HPG', 'VIC', 'MWG'] + default_tickers
        
        selected_tickers = st.multiselect(
            "Chọn các mã cổ phiếu trong danh mục của bạn:", 
            options=list(set(available_options)), # Lọc trùng lặp
            default=default_tickers
        )
    with col2:
        days_back = st.selectbox("Khung thời gian (Ngày):", [90, 180, 365, 730, 1825], index=2)
        
    if not selected_tickers:
        st.warning("Vui lòng chọn ít nhất một mã cổ phiếu.")
        return
        
    with st.spinner("Đang đồng bộ ma trận giá danh mục..."):
        portfolio_df = load_multiple_tickers(selected_tickers, days_back)
        
    if portfolio_df.empty:
        st.error("Không có dữ liệu cho các mã đã chọn.")
        return
        
    # --- CORE LOGIC: CHUẨN HÓA DỮ LIỆU TỶ SUẤT LỢI NHUẬN ---
    # Chia mọi giá trị cho mức giá ở dòng đầu tiên (iloc[0]), trừ đi 1 và nhân 100 để ra số %
    normalized_df = (portfolio_df / portfolio_df.iloc[0] - 1) * 100
    
    # --- RENDER BIỂU ĐỒ ---
    st.subheader("Biểu đồ Hiệu suất Tương đối (%)")
    
    fig = px.line(
        normalized_df, 
        x=normalized_df.index, 
        y=normalized_df.columns,
        labels={'value': 'Tỷ suất lợi nhuận (%)', 'Date': 'Thời gian', 'variable': 'Mã CP'}
    )
    
    # Tùy chỉnh Layout cho mượt mà
    fig.update_layout(
        hovermode="x unified",
        height=550,
        margin=dict(l=0, r=0, t=10, b=0),
        legend_title_text="Cổ phiếu"
    )
    
    # Thêm đường tham chiếu 0% (Hòa vốn) để làm mốc so sánh trực quan
    fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5, annotation_text="0% (Hòa vốn)")
    
    st.plotly_chart(fig, width="stretch")

if __name__ == "__main__":
    render_portfolio_page()
    