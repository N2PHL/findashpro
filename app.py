import streamlit as st

def render_homepage():
    # 1. Quản lý trạng thái toàn cục (Session State)
    # Khởi tạo giá trị mặc định nếu chưa có
    if 'ticker' not in st.session_state:
        st.session_state['ticker'] = 'VCB'

    # 2. Xây dựng Sidebar y hệt bản thiết kế ban đầu
    st.sidebar.markdown("### ⚙️ Bảng Điều Khiển")
    st.sidebar.divider()
    
    # Text input liên kết trực tiếp với session_state, tự động viết hoa
    input_ticker = st.sidebar.text_input(
        "Nhập mã cổ phiếu (Ticker):", 
        value=st.session_state['ticker']
    ).upper()
    
    # Cập nhật state nếu người dùng nhập mã mới
    if input_ticker != st.session_state['ticker']:
        st.session_state['ticker'] = input_ticker
        # Tải lại trang để cập nhật thông tin ngay lập tức
        st.rerun()

    # 3. Tùy chỉnh CSS cho giao diện Terminal
    st.markdown("""
        <style>
        .terminal-header {
            font-family: 'Courier New', Courier, monospace;
            color: #1E88E5;
            margin-bottom: 0px;
        }
        .subtitle {
            font-size: 1.1rem;
            color: #555;
            margin-bottom: 2rem;
        }
        </style>
    """, unsafe_allow_html=True)

    # 4. Header Trang Chủ
    st.markdown('<h1 class="terminal-header">FinDash Pro Terminal</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Hệ thống Phân tích Định lượng & Kiểm thử Chiến lược Giao dịch</p>', unsafe_allow_html=True)

    # 5. Thanh trạng thái hệ thống
    st.info(f"🟢 **System Status:** Đang kết nối luồng dữ liệu toàn cầu. Mã cổ phiếu kích hoạt trên toàn hệ thống: **{st.session_state['ticker']}**")
    
    st.divider()

    # 6. Bố cục Grid Layout cho các Module
    st.subheader("Bảng Điều Khiển Trung Tâm (Command Center)")
    
    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.markdown("### 📊 Dữ Liệu & Cơ Bản")
            st.markdown("**1. Summary:**")
            st.caption("Tổng quan chỉ số tài chính, định giá và diễn biến giao dịch theo thời gian thực.")
            st.markdown("**2. Advanced Chart:**")
            st.caption("Biểu đồ kỹ thuật tương tác sâu, tích hợp đa chỉ báo và khối lượng.")
            st.markdown("**3. Financials:**")
            st.caption("Trích xuất trực tiếp BCTC và Ratios từ hệ thống API tiêu chuẩn quốc tế.")

    with col2:
        with st.container(border=True):
            st.markdown("### ⚙️ Định Lượng & Rủi Ro")
            st.markdown("**4. Risk Analytics:**")
            st.caption("Đánh giá rủi ro toàn diện: Đo lường rủi ro hệ thống (Hệ số Beta, Alpha) qua mô hình CAPM và dự phóng rủi ro đuôi (VaR) bằng mô phỏng ngẫu nhiên Monte Carlo.")
            st.markdown("**5. Alpha Backtest:**")
            st.caption("Thiết kế, kiểm thử và tối ưu hóa các biểu thức chiến lược giao dịch (Alpha Factors).")
            st.markdown("**6. Risk Optimization:**")
            st.caption("Điều chỉnh tỷ trọng, tối ưu hóa danh mục theo ranh giới hiệu quả (Efficient Frontier).")

    with col3:
        with st.container(border=True):
            st.markdown("### 💼 Quản Quản & Trợ Lý")
            st.markdown("**7. Portfolio:**")
            st.caption("Theo dõi hiệu suất danh mục tổng thể, phân bổ tài sản và PnL thực tế.")
            st.markdown("**8. AI Assistant:**")
            st.caption("Trợ lý ngôn ngữ lớn hỗ trợ giải đáp thuật toán, phân tích tin tức và gợi ý code.")

    st.divider()
    
    # 7. Footer
    st.caption("© 2026 FinDash Pro. Dữ liệu được tính toán theo thời gian thực. Khuyến nghị thiết lập giao diện Dark Mode để tối ưu trải nghiệm.")

if __name__ == "__main__":
    render_homepage()