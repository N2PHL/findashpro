# pages/3_📑_Financials.py
import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data.yfinance_client import fetch_financial_ratios, fetch_income_statement

def render_financials_page():
    st.title("📑 Phân Tích Cơ Bản (Yahoo Finance API)")
    st.markdown("Luồng dữ liệu toàn cầu, đảm bảo kết nối ổn định và xuyên suốt mọi tường lửa.")
    
    st.sidebar.header("Cấu hình Tra cứu")
    ticker = st.sidebar.text_input("Nhập mã cổ phiếu:", value="VNM").upper()
    
    period_choice = st.sidebar.radio("Kỳ báo cáo", options=["Theo Quý", "Theo Năm"])
    is_yearly = True if period_choice == "Theo Năm" else False

    tab1, tab2 = st.tabs(["📈 Chỉ Số Tổng Quan (Ratios)", "📊 Kết Quả Kinh Doanh"])
    
    with tab1:
        st.subheader(f"Chỉ số tài chính trọng yếu - Mã: {ticker}")
        with st.spinner("Đang trích xuất dữ liệu từ hệ thống toàn cầu..."):
            df_ratios = fetch_financial_ratios(ticker)
            
            if not df_ratios.empty:
                # Dùng .T để lật dọc bảng 1 dòng cho đẹp mắt
                st.dataframe(df_ratios.T, width="stretch")
            else:
                st.warning(f"Không lấy được dữ liệu chỉ số cho mã {ticker}. (Hoặc mã không tồn tại trên hệ thống)")
                
    with tab2:
        st.subheader(f"Báo cáo Kết quả kinh doanh ({period_choice}) - Mã: {ticker}")
        with st.spinner("Đang xử lý ma trận báo cáo..."):
            df_income = fetch_income_statement(ticker, is_yearly=is_yearly)
            
            if not df_income.empty:
                # Chuyển đổi định dạng tên cột (datetime) thành chuỗi ngày tháng dễ nhìn (YYYY-MM-DD)
                df_income.columns = [col.strftime('%Y-%m-%d') if hasattr(col, 'strftime') else col for col in df_income.columns]
                st.dataframe(df_income, width="stretch")
            else:
                st.warning(f"Không tìm thấy báo cáo kết quả kinh doanh cho mã {ticker}.")

if __name__ == "__main__":
    render_financials_page()
    