# pages/3_📑_Financials.py — yêu cầu [3]: thống kê, tài chính, phân tích giá một cổ phiếu
import streamlit as st

from core.quantitative import describe_returns, log_returns
from data.dnse_client import get_ohlcv
from data.yfinance_client import MARKETS, coverage, fetch_financial_ratios, fetch_statement
from ui.charts import apply_theme
from ui.components import (guard_data, guard_model, note, page_header, period_selector,
                           setup_page, sidebar_assumptions, source_badge, ticker_selector)
from utils.config import ACCENT, ACCENT_UP

import plotly.graph_objects as go
import numpy as np
from scipy import stats


def render_financials_page() -> None:
    setup_page("Financials", "📑")
    ticker = ticker_selector("fin")
    days = period_selector("fin", 365)
    market = st.sidebar.selectbox("Thị trường (dữ liệu cơ bản)", list(MARKETS))
    suffix = MARKETS[market]
    sidebar_assumptions()

    page_header(f"Phân tích cơ bản & thống kê · {ticker}",
                "Thống kê mô tả chuỗi lợi suất, chỉ số định giá và ba báo cáo tài chính")

    tab_stat, tab_ratio, tab_stmt = st.tabs(
        ["📐 Thống kê giá", "📈 Chỉ số định giá", "📊 Báo cáo tài chính"])

    # ---------------- Thống kê mô tả ----------------
    with tab_stat:
        df, source = get_ohlcv(ticker, days)
        guard_data(df, ticker, min_rows=31)
        source_badge(source)

        table = guard_model(describe_returns, df["close"])
        if table is not None:
            r = log_returns(df["close"])
            c1, c2 = st.columns([1, 1.35])
            with c1:
                st.dataframe(table, use_container_width=True, hide_index=True)
            with c2:
                fig = go.Figure()
                fig.add_trace(go.Histogram(x=r, nbinsx=60, name="Thực tế",
                                           marker_color=ACCENT, opacity=0.75,
                                           histnorm="probability density"))
                xs = np.linspace(r.min(), r.max(), 200)
                fig.add_trace(go.Scatter(
                    x=xs, y=stats.norm.pdf(xs, r.mean(), r.std(ddof=1)),
                    mode="lines", name="Phân phối chuẩn tương đương",
                    line=dict(color=ACCENT_UP, width=2, dash="dash")))
                fig.update_xaxes(title_text="Log return theo phiên")
                st.plotly_chart(apply_theme(fig, 380, "Phân phối lợi suất"),
                                use_container_width=True)

            note("<b>Kiểm định giả định phân phối chuẩn.</b> Đường đứt nét là hàm mật độ "
                 "chuẩn N(μ̂, σ̂²) ước lượng từ chính chuỗi lợi suất, đặt chồng lên histogram "
                 "thực nghiệm để đối chiếu trực quan. Hai chỉ tiêu định lượng đi kèm: "
                 "<b>kurtosis thừa</b> đo độ dày đuôi so với phân phối chuẩn (bằng 0 nếu "
                 "chuẩn, dương nếu leptokurtic), và thống kê <b>Jarque–Bera</b> kiểm định "
                 "đồng thời độ lệch và độ nhọn, tuân theo phân phối χ² với 2 bậc tự do dưới "
                 "giả thuyết H₀ rằng chuỗi phân phối chuẩn. p-value &lt; 0,05 dẫn tới bác bỏ "
                 "H₀. Đây là hiện tượng đã được ghi nhận từ <b>Mandelbrot (1963)</b> và "
                 "<b>Fama (1965)</b>: lợi suất tài sản có đuôi dày hơn phân phối chuẩn. Hệ "
                 "quả trực tiếp là mô hình GBM — vốn giả định lợi suất log phân phối chuẩn — "
                 "sẽ <b>ước lượng thiếu xác suất của các biến động cực đoan</b>, khiến VaR "
                 "tính theo GBM thấp hơn rủi ro thực. Phương án Bootstrap ở trang Risk "
                 "Analytics rút mẫu trực tiếp từ phân phối thực nghiệm nên không áp đặt giả "
                 "định này; chênh lệch giữa hai phương pháp chính là thước đo mức độ ảnh "
                 "hưởng của việc vi phạm giả định.")

    # ---------------- Chỉ số định giá ----------------
    with tab_ratio:
        with st.spinner("Đang tải chỉ số định giá…"):
            ratios = fetch_financial_ratios(ticker, suffix)

        if ratios.empty:
            st.warning(f"Yahoo Finance không trả về dữ liệu cho mã **{ticker}{suffix}**.")
        else:
            miss = coverage(ratios)
            if miss > 0.4:
                note(f"Yahoo Finance thiếu <b>{miss:.0%}</b> số trường cho mã này. Các ô "
                     f"ghi &quot;—&quot; là <b>dữ liệu thiếu, không phải giá trị bằng 0</b>. "
                     f"Với cổ phiếu niêm yết tại Việt Nam, độ phủ dữ liệu cơ bản của Yahoo "
                     f"rất hạn chế; nguồn nội địa (vnstock, TCBS) sẽ đầy đủ hơn.")
            st.dataframe(ratios.drop(columns=["_missing"]),
                         use_container_width=True, hide_index=True)

    # ---------------- Báo cáo tài chính ----------------
    with tab_stmt:
        c1, c2 = st.columns(2)
        kind_label = c1.radio("Báo cáo", ["Kết quả kinh doanh", "Cân đối kế toán", "Lưu chuyển tiền tệ"],
                              horizontal=True)
        period = c2.radio("Kỳ", ["Theo quý", "Theo năm"], horizontal=True)
        kind = {"Kết quả kinh doanh": "income", "Cân đối kế toán": "balance",
                "Lưu chuyển tiền tệ": "cashflow"}[kind_label]

        with st.spinner("Đang tải báo cáo…"):
            stmt = fetch_statement(ticker, kind, period == "Theo năm", suffix)

        if stmt.empty:
            st.warning(f"Không có {kind_label.lower()} cho mã **{ticker}{suffix}**.")
        else:
            st.dataframe(stmt, use_container_width=True)
            note("<b>Xử lý dữ liệu khuyết.</b> Ô trống biểu thị trường mà nguồn không "
                 "cung cấp, và được giữ nguyên trạng thái khuyết thay vì quy về 0. Phân "
                 "biệt này có ý nghĩa thực chất trong phân tích báo cáo tài chính: một kỳ "
                 "khuyết doanh thu nếu bị điền 0 sẽ làm mọi tỷ suất suy ra từ nó (biên lợi "
                 "nhuận, vòng quay tài sản) hoặc bằng 0 hoặc không xác định do chia cho 0, "
                 "đồng thời kéo lệch mọi thống kê tổng hợp theo chuỗi thời gian. Nguyên tắc "
                 "chung: giá trị khuyết phải được loại khỏi mẫu (listwise deletion) hoặc "
                 "khai báo rõ phương pháp nội suy, không được ngầm thay bằng một con số.")


if __name__ == "__main__":
    render_financials_page()
