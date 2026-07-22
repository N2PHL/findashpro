# app.py module
import streamlit as st

def initialize_app():
    """Khởi tạo cấu hình trang và các biến trạng thái toàn cục."""
    
    # 1. Cấu hình Page (Phải luôn là lệnh Streamlit đầu tiên được gọi)
    st.set_page_config(
        page_title="FinDash Pro - Quantitative Platform",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 2. Khởi tạo Session State để chia sẻ dữ liệu giữa các trang
    if 'current_ticker' not in st.session_state:
        # Sử dụng một rổ cổ phiếu bất động sản/hạ tầng tiêu biểu làm mặc định
        st.session_state['current_ticker'] = 'VPH'
        
def build_sidebar():
    """Xây dựng thanh điều hướng và bộ lọc toàn cục ở Sidebar."""
    st.sidebar.title("⚙️ Bảng Điều Khiển")
    st.sidebar.markdown("---")
    
    # Input lấy mã cổ phiếu, tự động in hoa và lưu trực tiếp vào session_state
    ticker_input = st.sidebar.text_input(
        "Nhập mã cổ phiếu (Ticker):", 
        value=st.session_state['current_ticker']
    ).upper()
    
    # Cập nhật trạng thái nếu có thay đổi
    if ticker_input != st.session_state['current_ticker']:
        st.session_state['current_ticker'] = ticker_input
        st.sidebar.success(f"Đã chuyển sang mã: {ticker_input}")

def main():
    """Hàm chạy chính của ứng dụng."""
    initialize_app()
    build_sidebar()
    
    # Nội dung trang chủ (Landing Page)
    st.title("Trang Chủ Phân Tích Định Lượng")
    st.markdown("""
    Chào mừng đến với **FinDash Pro**. Hệ thống đã được tái cấu trúc hoàn toàn.
    
    👈 Vui lòng chọn các module phân tích từ thanh công cụ bên trái:
    *   **Summary:** Tổng quan chỉ số tài chính.
    *   **Advanced Chart:** Biểu đồ kỹ thuật tương tác.
    *   **Monte Carlo:** Chạy mô phỏng định lượng và đo lường rủi ro (VaR).
    """)
    
    st.info(f"Mã cổ phiếu đang chọn trên toàn hệ thống: **{st.session_state['current_ticker']}**")

if __name__ == "__main__":
    main()