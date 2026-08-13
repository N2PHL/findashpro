# app.py — điểm vào ứng dụng.  Chạy: streamlit run app.py
"""
Trang chủ FinDash Pro — hệ thống phân tích định lượng thị trường chứng khoán Việt Nam.

Ứng dụng gồm tám module, đi từ mô tả dữ liệu tới mô hình định giá tài sản và tối ưu
danh mục. Mọi trang đọc chung một mã cổ phiếu từ session state và chung một bộ tham
số thị trường khai báo ở utils/config.py, để các con số giữa các trang so sánh được
với nhau.

Phạm vi dữ liệu được nêu tường minh ở cuối trang chủ: giá cuối phiên từ DNSE/entrade
cho cổ phiếu niêm yết tại Việt Nam, dữ liệu cơ bản từ Yahoo Finance với độ phủ hạn
chế. Đây là sản phẩm học thuật, không phải khuyến nghị đầu tư.
"""
import streamlit as st

from ui.components import page_header, setup_page, sidebar_assumptions, ticker_selector
from utils.config import PRICE_UNIT, RISK_FREE_RATE

MODULES = [
    ("📊 Dữ liệu & Cơ bản", [
        ("1 · Summary", "Hồ sơ doanh nghiệp, giá, thanh khoản và biên độ 52 tuần.", "[1]"),
        ("2 · Advanced Chart", "Nến/Line/OHLC, lấy mẫu ngày–tuần–tháng–quý, SMA/EMA/Bollinger/RSI.", "[2]"),
        ("3 · Financials", "Thống kê mô tả giá, chỉ số định giá, KQKD – CĐKT – LCTT.", "[3]"),
    ]),
    ("⚙️ Định lượng & Rủi ro", [
        ("4 · Risk Analytics", "Monte Carlo (GBM & Bootstrap), VaR/CVaR, CAPM và APT cho một mã.", "[4][5]"),
        ("5 · Alpha Backtest", "Kiểm thử tín hiệu, có phí giao dịch, chặn bán khống, ràng buộc T+2.", "—"),
        ("6 · Risk Optimization", "Đường biên hiệu quả giải bằng tối ưu, VaR/CVaR danh mục, kiểm định Kupiec.", "[4]"),
    ]),
    ("💼 Quản lý & Trợ lý", [
        ("7 · Portfolio", "NAV, PnL, phân bổ tài sản và CAPM/APT ở cấp danh mục.", "[4]"),
        ("8 · AI Assistant", "Hỏi đáp về phương pháp định lượng, có nạp số liệu thật của mã đang chọn.", "—"),
    ]),
]


def render_homepage() -> None:
    setup_page("Terminal", "📊")
    ticker = ticker_selector("home")
    sidebar_assumptions()

    page_header("FinDash Pro Terminal",
                "Hệ thống phân tích định lượng thị trường chứng khoán Việt Nam")

    st.info(f"Mã đang chọn trên toàn hệ thống: **{ticker}** — mọi trang đều đọc cùng "
            f"giá trị này từ session state.")

    cols = st.columns(3)
    for col, (group, items) in zip(cols, MODULES):
        with col, st.container(border=True):
            st.markdown(f"### {group}")
            for name, desc, req in items:
                st.markdown(f"**{name}**  ·  `{req}`")
                st.caption(desc)

    st.divider()
    st.markdown("#### Nguồn dữ liệu và giả định")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"- **Giá:** DNSE / entrade `chart-api/v2`, cuối phiên, đơn vị {PRICE_UNIT}\n"
            f"- **Cơ bản:** Yahoo Finance — độ phủ hạn chế với cổ phiếu Việt Nam\n"
            f"- **Phạm vi:** cổ phiếu và chỉ số niêm yết tại Việt Nam"
        )
    with c2:
        st.markdown(
            f"- **Lãi suất phi rủi ro:** {RISK_FREE_RATE:.2%}/năm (một giá trị duy nhất)\n"
            f"- **Lợi suất:** log return, thống nhất mọi mô hình\n"
            f"- **Giả định thị trường:** không bán khống, thanh toán T+2"
        )
    st.caption("Sản phẩm học thuật. Không phải khuyến nghị đầu tư.")


if __name__ == "__main__":
    render_homepage()
