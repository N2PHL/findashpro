# pages/3_📑_Financials.py
import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data.yfinance_client import fetch_financial_ratios, fetch_income_statement

def render_financials_page():
    # --- 1. QUẢN LÝ TRẠNG THÁI (SESSION STATE) ---
    if 'ticker' not in st.session_state:
        st.session_state['ticker'] = 'VCB'

    # --- 2. SIDEBAR ĐỒNG BỘ ---
    st.sidebar.markdown("### ⚙️ Bảng Điều Khiển")
    st.sidebar.divider()
    
    input_ticker = st.sidebar.text_input(
        "Nhập mã cổ phiếu (Ticker):", 
        value=st.session_state['ticker'],
        key="financials_ticker_input"
    ).upper()
    
    if input_ticker != st.session_state['ticker']:
        st.session_state['ticker'] = input_ticker
        st.rerun()

    current_ticker = st.session_state['ticker']
    
    # Cấu hình đặc thù của trang Financials
    st.sidebar.markdown("**Cấu hình Báo cáo**")
    period_choice = st.sidebar.radio("Kỳ báo cáo:", options=["Theo Quý", "Theo Năm"])
    is_yearly = True if period_choice == "Theo Năm" else False

    # --- 3. GIAO DIỆN CHÍNH (COMMAND CENTER) ---
    st.markdown("""
        <style>
        .terminal-header {
            font-family: 'Courier New', Courier, monospace;
            color: #ff9900;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f'<h1 class="terminal-header">📑 Phân Tích Cơ Bản: {current_ticker}</h1>', unsafe_allow_html=True)
    st.caption("Trích xuất Báo cáo tài chính và chỉ số định giá (Ratios) trực tiếp từ nền tảng dữ liệu toàn cầu (Yahoo Finance API).")
    
    # --- 4. RENDER TABS VÀ DỮ LIỆU ---
    tab1, tab2 = st.tabs(["📈 Chỉ Số Tổng Quan (Ratios)", "📊 Kết Quả Kinh Doanh"])
    
    with tab1:
        st.markdown(f"### Chỉ số tài chính trọng yếu")
        with st.spinner(f"Đang trích xuất dữ liệu định giá từ hệ thống toàn cầu cho mã {current_ticker}..."):
            df_ratios = fetch_financial_ratios(current_ticker)
            
            if not df_ratios.empty:
                # Dùng container để tạo khung viền nổi bật như Terminal
                with st.container(border=True):
                    # Dùng .T để lật dọc bảng 1 dòng cho đẹp mắt
                    st.dataframe(df_ratios.T, width='stretch')
            else:
                st.warning(f"Không lấy được dữ liệu chỉ số cho mã {current_ticker}. (Hoặc mã không tồn tại trên hệ thống)")
                
    with tab2:
        st.markdown(f"### Báo cáo Kết quả kinh doanh ({period_choice})")
        with st.spinner(f"Đang xử lý ma trận báo cáo cho mã {current_ticker}..."):
            df_income = fetch_income_statement(current_ticker, is_yearly=is_yearly)
            
            if not df_income.empty:
                # Chuyển đổi định dạng tên cột (datetime) thành chuỗi ngày tháng dễ nhìn (YYYY-MM-DD)
                df_income.columns = [col.strftime('%Y-%m-%d') if hasattr(col, 'strftime') else col for col in df_income.columns]
                with st.container(border=True):
                    st.dataframe(df_income, width='stretch')
            else:
                st.warning(f"Không tìm thấy báo cáo kết quả kinh doanh cho mã {current_ticker}.")

if __name__ == "__main__":
    render_financials_page()
