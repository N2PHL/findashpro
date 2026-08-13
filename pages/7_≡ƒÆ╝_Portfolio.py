# pages/7_💼_Portfolio.py — yêu cầu [4]: PHÂN TÍCH DANH MỤC (NAV, PnL, phân bổ, CAPM, APT)
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.portfolio import apt, build_factors, capm, normalize_weights, portfolio_series
from core.quantitative import describe_returns, log_returns
from data.dnse_client import get_ohlcv
from ui.charts import apply_theme
from ui.components import (guard_model, multi_ticker_selector, note, page_header,
                           period_selector, setup_page, sidebar_assumptions)
from utils.config import (ACCENT, ACCENT_UP, DEFAULT_PORTFOLIO, MARKET_INDEX,
                          MUTED, SIZE_INDEX)


@st.cache_data(ttl=300, show_spinner=False)
def load_prices(tickers: tuple[str, ...], days: int) -> tuple[pd.DataFrame, list[str]]:
    series, failed = {}, []
    for t in tickers:
        df, _ = get_ohlcv(t, days, allow_mock=False)
        if df.empty or len(df) < 30:
            failed.append(t)
        else:
            series[t] = df["close"]
    if not series:
        return pd.DataFrame(), failed
    return pd.DataFrame(series).dropna(), failed


def render_portfolio_page() -> None:
    setup_page("Portfolio", "💼")
    page_header("Danh mục đầu tư",
                "Giá trị ròng, lãi/lỗ, phân bổ tài sản và mô hình CAPM/APT ở cấp danh mục")

    tickers = multi_ticker_selector("pf", "Cổ phiếu trong danh mục", list(DEFAULT_PORTFOLIO))
    days = period_selector("pf", 365)
    capital = st.sidebar.number_input("Vốn đầu tư (VND)", value=500_000_000, step=50_000_000)
    sidebar_assumptions()

    st.markdown("##### 1 · Tỷ trọng phân bổ")
    st.caption("Tỷ trọng wᵢ xác định danh mục. Lợi suất danh mục là tổ hợp tuyến tính "
               "R_p = Σ wᵢRᵢ, còn phương sai thì không — σ²_p = wᵀΣw phụ thuộc vào toàn bộ "
               "ma trận hiệp phương sai, và chính số hạng chéo tạo ra lợi ích đa dạng hóa.")
    cols = st.columns(min(len(tickers), 6))
    raw_w = {}
    for i, t in enumerate(tickers):
        raw_w[t] = cols[i % len(cols)].number_input(
            f"{t} (%)", min_value=0.0, max_value=100.0,
            value=float(DEFAULT_PORTFOLIO.get(t, 1 / len(tickers)) * 100),
            step=5.0, key=f"w_{t}")

    if sum(raw_w.values()) <= 0:
        st.error("Tổng tỷ trọng phải lớn hơn 0.")
        st.stop()
    weights = normalize_weights(raw_w)
    if abs(sum(raw_w.values()) - 100) > 0.5:
        st.info(f"Tổng tỷ trọng nhập vào là {sum(raw_w.values()):.1f}% — đã chuẩn hóa về 100%.")

    prices, failed = load_prices(tuple(tickers), days)
    if failed:
        st.warning(f"Bỏ qua mã không có dữ liệu: **{', '.join(failed)}**")
    if prices.empty:
        st.error("Không có phiên nào mà tất cả các mã đều có giá.")
        st.stop()

    weights = normalize_weights({k: v for k, v in weights.items() if k in prices.columns})
    pf = guard_model(portfolio_series, prices, weights, capital)
    if pf is None:
        st.stop()

    # ---------------- NAV & PnL ----------------
    st.markdown("##### 2 · Giá trị ròng và lãi/lỗ")
    nav_now = float(pf["nav"].iloc[-1])
    pnl = float(pf["pnl"].iloc[-1])
    ret = float(pf["return_pct"].iloc[-1])
    pf_ret = log_returns(pf["nav"])
    peak = pf["nav"].cummax()
    mdd = float(((pf["nav"] - peak) / peak).min())

    k = st.columns(5)
    k[0].metric("Vốn ban đầu", f"{capital/1e6:,.0f} tr")
    k[1].metric("NAV hiện tại", f"{nav_now/1e6:,.1f} tr", delta=f"{ret:+.2%}")
    k[2].metric("Lãi/lỗ (PnL)", f"{pnl/1e6:+,.1f} tr")
    k[3].metric("Biến động năm", f"{pf_ret.std(ddof=1)*np.sqrt(252):.2%}")
    k[4].metric("Max Drawdown", f"{mdd:.2%}")

    c1, c2 = st.columns([1.6, 1])
    with c1:
        bench_df, _ = get_ohlcv(MARKET_INDEX, days)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=pf.index, y=pf["nav"], name="Danh mục",
                                 line=dict(color=ACCENT, width=2.2)))
        if not bench_df.empty:
            bench = bench_df["close"].reindex(pf.index).ffill()
            fig.add_trace(go.Scatter(x=pf.index, y=capital * bench / bench.iloc[0],
                                     name=MARKET_INDEX,
                                     line=dict(color=MUTED, dash="dash", width=1.5)))
        fig.add_hline(y=capital, line_dash="dot", line_color=ACCENT_UP,
                      annotation_text="Vốn góp ban đầu — ngưỡng hòa vốn danh nghĩa")
        fig.update_yaxes(title_text="NAV (VND)")
        st.plotly_chart(apply_theme(fig, 420, "NAV danh mục so với chỉ số"),
                        use_container_width=True)
    with c2:
        pos_now = pf[[c for c in pf.columns if c.startswith("pos_")]].iloc[-1]
        pos_now.index = [c.replace("pos_", "") for c in pos_now.index]
        fig = px.pie(values=pos_now.to_numpy(), names=pos_now.index, hole=0.45)
        fig.update_traces(textinfo="label+percent")
        st.plotly_chart(apply_theme(fig, 420, "Phân bổ tài sản HIỆN TẠI"),
                        use_container_width=True)
        note("<b>Hiện tượng trôi tỷ trọng.</b> Biểu đồ thể hiện phân bổ <i>hiện tại</i>, "
             "đã lệch khỏi tỷ trọng mục tiêu ban đầu do danh mục vận hành theo chiến lược "
             "mua và nắm giữ, không tái cân bằng. Cơ chế: mã tăng giá mạnh hơn sẽ tự động "
             "chiếm tỷ trọng lớn dần, khiến rủi ro danh mục dịch chuyển về phía mã đó mà "
             "nhà đầu tư không ra quyết định nào. Đây là lý do các nghiên cứu về phân bổ "
             "tài sản phân biệt rõ <b>trọng số mục tiêu</b> với <b>trọng số thực hiện</b>: "
             "so sánh hiệu suất giữa hai danh mục chỉ có ý nghĩa khi cùng quy ước tái cân "
             "bằng, vì bản thân tần suất tái cân bằng đã là một quyết định đầu tư.")

    # ---------------- Đóng góp ----------------
    st.markdown("##### 3 · Đóng góp của từng mã")
    contrib = pd.DataFrame({
        "Mã": list(weights),
        "Tỷ trọng đầu kỳ": [f"{weights[t]:.1%}" for t in weights],
        "Lợi suất mã": [f"{prices[t].iloc[-1]/prices[t].iloc[0]-1:+.2%}" for t in weights],
        "Đóng góp vào PnL (tr)": [
            (pf[f"pos_{t}"].iloc[-1] - capital * weights[t]) / 1e6 for t in weights],
    })
    st.dataframe(contrib.style.format({"Đóng góp vào PnL (tr)": "{:+,.2f}"}),
                 use_container_width=True, hide_index=True)

    # ---------------- CAPM & APT cấp danh mục ----------------
    st.markdown("##### 4 · CAPM và APT cho DANH MỤC")
    st.caption("Hai mô hình được ước lượng trên chuỗi lợi suất của NAV danh mục, không "
               "phải của từng mã riêng lẻ. Beta danh mục bằng bình quân gia quyền beta "
               "các thành phần, nhưng alpha và R² thì không có tính chất cộng tính đó — "
               "chúng phải được ước lượng lại trên chuỗi tổng hợp.")

    mkt_df, _ = get_ohlcv(MARKET_INDEX, days)
    if mkt_df.empty:
        st.warning(f"Không tải được {MARKET_INDEX} để chạy mô hình.")
        return

    t1, t2, t3 = st.tabs(["📐 CAPM danh mục", "🧮 APT danh mục", "📊 Thống kê danh mục"])

    with t1:
        res = guard_model(capm, pf_ret, log_returns(mkt_df["close"]))
        if res is not None:
            k = st.columns(5)
            k[0].metric("Beta danh mục", f"{res['beta']:.3f}",
                        help=f"t = {res['beta_tstat']:.2f}")
            k[1].metric("Alpha (năm hóa)", f"{res['alpha_annual']:+.2%}",
                        help=f"p = {res['alpha_pvalue']:.4f}")
            k[2].metric("R²", f"{res['r_squared']:.1%}")
            k[3].metric("Lợi suất yêu cầu", f"{res['required_return']:+.2%}")
            k[4].metric("Jensen's Alpha", f"{res['jensen_alpha']:+.2%}")
            sig = "có ý nghĩa thống kê" if res["alpha_significant"] else "KHÔNG có ý nghĩa thống kê"
            note(f"<b>Diễn giải hệ số.</b> Beta = {res['beta']:.2f} là độ nhạy của danh "
                 f"mục với lợi suất thị trường: khi thị trường biến động 1%, danh mục biến "
                 f"động khoảng {res['beta']:.2f}% theo cùng chiều, tức "
                 f"<b>{'khuếch đại' if res['beta'] > 1 else 'giảm nhẹ'}</b> rủi ro hệ thống. "
                 f"R² = {res['r_squared']:.1%} cho biết tỷ lệ phương sai danh mục được nhân "
                 f"tố thị trường giải thích; phần còn lại là rủi ro riêng có, và tỷ lệ này "
                 f"càng cao thì danh mục càng gần với một vị thế thuần thị trường. "
                 f"Alpha Jensen = {res['alpha_annual']:+.2%}/năm và <b>{sig}</b> ở mức ý "
                 f"nghĩa 5% (p = {res['alpha_pvalue']:.4f}). Alpha chỉ nên được diễn giải "
                 f"như lợi suất vượt trội đã điều chỉnh rủi ro khi hệ số có ý nghĩa thống "
                 f"kê; một alpha dương nhưng p-value lớn không phân biệt được với nhiễu "
                 f"ngẫu nhiên.")

    with t2:
        size_df, _ = get_ohlcv(SIZE_INDEX, days)
        factors = build_factors(mkt_df["close"],
                                size_df["close"] if not size_df.empty else None)
        res_apt = guard_model(apt, pf_ret, factors)
        if res_apt is not None:
            k = st.columns(3)
            k[0].metric("R² hiệu chỉnh", f"{res_apt['adj_r_squared']:.1%}")
            k[1].metric("F-test p-value", f"{res_apt['f_pvalue']:.4f}")
            k[2].metric("Alpha (năm hóa)", f"{res_apt['alpha_annual']:+.2%}")
            st.dataframe(res_apt["table"].style.format({
                "Hệ số β": "{:.4f}", "Sai số chuẩn": "{:.4f}",
                "t-statistic": "{:.2f}", "p-value": "{:.4f}"}),
                use_container_width=True, hide_index=True)
            st.caption("VIF: " + ", ".join(f"{k_} = {v:.2f}" for k_, v in res_apt["vif"].items()))

    with t3:
        table = guard_model(describe_returns, pf["nav"])
        if table is not None:
            st.dataframe(table, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    render_portfolio_page()
