# 3_📑_Financials.py module
# pages/3_📑_Financials.py
import streamlit as st
import pandas as pd
import sys
import os

# Thiết lập đường dẫn absolute
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# -----------------------------------------------------------------------------
# [DATA LAYER MOCK] 
# Ghi chú: API của DNSE ở bước trước chỉ cung cấp dữ liệu giá (OHLCV).
# Để lấy Báo cáo tài chính (BCTC) thị trường VN, hệ thống thực tế thường gọi 
# qua public API của TCBS hoặc FiinTrade. Dưới đây là hàm Mock Data giả lập 
# luồng dữ liệu trả về để hoàn thiện kiến trúc UI.
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600) # Cache BCTC lâu hơn (1 giờ) vì dữ liệu này ít thay đổi
def fetch_fundamental_data(ticker: str, statement_type: str, is_yearly: bool) -> pd.DataFrame:
    """Giả lập Data Layer lấy Báo cáo tài chính và Chỉ số định giá."""
    
    # Dữ liệu giả lập (Mock) cho Bảng cân đối kế toán
    if statement_type == 'balance_sheet':
        data = {
            'Chỉ tiêu': ['Tài sản ngắn hạn', 'Tài sản dài hạn', 'Nợ phải trả', 'Vốn chủ sở hữu'],
            '2023': [15000, 25000, 18000, 22000],
            '2022': [14000, 24000, 17500, 20500],
            '2021': [12000, 22000, 16000, 18000]
        }
    # Dữ liệu giả lập cho Báo cáo kết quả kinh doanh
    elif statement_type == 'income_statement':
        data = {
            'Chỉ tiêu': ['Doanh thu thuần', 'Giá vốn hàng bán', 'Lợi nhuận gộp', 'LNST của CĐ Cty mẹ'],
            '2023': [50000, 35000, 15000, 5000],
            '2022': [45000, 32000, 13000, 4200],
            '2021': [40000, 29000, 11000, 3500]
        }
    # Dữ liệu giả lập cho Chỉ số định giá (Statistics)
    else:
        data = {
            'Chỉ số': ['P/E (Lần)', 'P/B (Lần)', 'EPS (VND)', 'BVPS (VND)', 'ROE (%)', 'ROA (%)'],
            'Giá trị': [12.5, 1.8, 3500, 15000, 18.5, 7.2]
        }
        
    df = pd.DataFrame(data)
    df.set_index(df.columns[0], inplace=True)
    return df

def render_financials_page():
    st.title("📑 Báo Cáo Tài Chính & Định Giá")
    
    ticker = st.session_state.get('current_ticker', 'VPH')
    st.markdown(f"Tra cứu hồ sơ cơ bản và cấu trúc tài chính của doanh nghiệp: **{ticker}**")
    
    # --- UI COMPONENT: TABS ---
    # Thay vì dùng radio button cồng kềnh, ta chia thành 3 Tabs gọn gàng
    tab_stats, tab_statements, tab_analysis = st.tabs([
        "📊 Chỉ số Định giá (Statistics)", 
        "🗂️ Báo cáo Tài chính (Financials)", 
        "🧠 Phân tích & Đánh giá (Analysis)"
    ])
    
    # --- TAB 1: CHỈ SỐ ĐỊNH GIÁ ---
    with tab_stats:
        st.subheader("Định giá & Hiệu quả hoạt động")
        df_stats = fetch_fundamental_data(ticker, 'statistics', True)
        
        # Format lại bảng hiển thị cho chuyên nghiệp
        st.dataframe(
            df_stats,
            use_container_width=True,
            height=250
        )
        
    # --- TAB 2: BÁO CÁO TÀI CHÍNH ---
    with tab_statements:
        col1, col2 = st.columns([1, 1])
        with col1:
            statement_type = st.selectbox(
                "Loại báo cáo:", 
                ['Bảng cân đối kế toán', 'Kết quả kinh doanh', 'Lưu chuyển tiền tệ']
            )
        with col2:
            period = st.radio("Kỳ báo cáo:", ['Năm (Yearly)', 'Quý (Quarterly)'], horizontal=True)
            
        # Ánh xạ (Mapping) lựa chọn UI vào biến logic
        type_map = {
            'Bảng cân đối kế toán': 'balance_sheet',
            'Kết quả kinh doanh': 'income_statement',
            'Lưu chuyển tiền tệ': 'cash_flow'
        }
        is_yearly = True if 'Năm' in period else False
        
        with st.spinner("Đang truy xuất hệ thống dữ liệu kế toán..."):
            df_financials = fetch_fundamental_data(ticker, type_map[statement_type], is_yearly)
            
        st.markdown(f"### {statement_type}")
        
        # Sử dụng st.table để in BCTC dạng văn bản trang trọng, không có thanh cuộn ngang
        st.table(df_financials)
        
    #    # --- TAB 3: PHÂN TÍCH (ANALYSIS) ---
    with tab_analysis:
        st.subheader("Đánh Giá Dựa Trên Yếu Tố Định Lượng (Factor-Based Analysis)")
        st.markdown("Tiếp cận theo tư duy quỹ định lượng: Phân rã rủi ro và chấm điểm Alpha.")
        
        # 1. Các chỉ số rủi ro hệ thống (Systematic Risk & Performance)
        # Trong thực tế, các chỉ số này sẽ được tính toán ở thư mục core/quantitative.py
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Sharpe Ratio", "1.45", "Hiệu suất tốt", delta_color="normal")
        c2.metric("Max Drawdown", "-15.2%", "Rủi ro kiểm soát", delta_color="inverse")
        c3.metric("Beta (vs VNINDEX)", "0.85", "Phòng thủ")
        c4.metric("Alpha (Kỳ vọng)", "+4.2%", "Outperform")
        
        st.markdown("---")
        
        # 2. Biểu đồ Radar (Spider Chart) chấm điểm Multi-Factor
        col_radar, col_text = st.columns([1, 1.2])
        
        with col_radar:
            # Mock data cho Factor Scores (Thang điểm từ 0 đến 100)
            categories = ['Định giá (Value)', 'Đà tăng trưởng (Momentum)', 'Chất lượng (Quality)', 'Biến động thấp (Low Vol)', 'Thanh khoản (Liquidity)']
            scores = [85, 40, 75, 90, 65]
            
            import plotly.graph_objects as go
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=scores,
                theta=categories,
                fill='toself',
                name=ticker,
                line_color='#00b4d8',
                fillcolor='rgba(0, 180, 216, 0.3)'
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=False,
                margin=dict(l=30, r=30, t=30, b=30),
                height=350
            )
            st.plotly_chart(fig_radar, use_container_width=True)
            
        with col_text:
            st.markdown("### Luận điểm Định lượng (Quant Rationale)")
            
            st.markdown(f"""
            Hệ thống quét qua các biểu thức Alpha và ghi nhận các tín hiệu thống kê đáng chú ý đối với **{ticker}**:
            
            * **Tín hiệu Value (Điểm: 85):** Z-score của P/E và P/B đang nằm ở mức -1.5 độ lệch chuẩn so với trung bình ngành. Mức định giá đang bị nén chặt.
            * **Tín hiệu Quality (Điểm: 75):** Cấu trúc vốn và biên lợi nhuận ổn định, thể hiện lợi thế cạnh tranh cốt lõi (Economic Moat) vững chắc.
            * **Tín hiệu Momentum (Điểm: 40):** Chưa có dòng tiền đột biến (Volume breakout) xác nhận xu hướng ngắn hạn. Cần chờ thêm tín hiệu xác nhận từ động lượng.
            """)
            
            st.info("💡 Tín hiệu thống kê: Hiện tượng Mean Reversion có xác suất 68% sẽ được kích hoạt tại vùng hỗ trợ hiện tại.")

if __name__ == "__main__":
    render_financials_page()
    