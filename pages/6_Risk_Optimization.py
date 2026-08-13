# pages/6_Risk_Optimization.py — yêu cầu [4]: tối ưu danh mục, đường biên hiệu quả, VaR
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.portfolio_opt import COV_METHODS, PortfolioOptimizer as Opt, covariance_matrix
from core.quantitative import log_returns
from data.dnse_client import get_ohlcv
from ui.charts import apply_theme
from ui.components import (guard_model, multi_ticker_selector, note, page_header,
                           period_selector, setup_page, sidebar_assumptions)
from utils.config import ACCENT, ACCENT_DOWN, ACCENT_UP


@st.cache_data(ttl=300, show_spinner=False)
def load_price_matrix(tickers: tuple[str, ...], days: int) -> tuple[pd.DataFrame, list[str]]:
    """
    Ghép ma trận giá đóng cửa của nhiều mã theo trục thời gian chung.

    Chỉ giữ những phiên mà TẤT CẢ các mã đều có giá (giao của các tập ngày). Điều
    này cần thiết vì ma trận hiệp phương sai phải được ước lượng trên cùng một bộ
    quan sát; nếu mỗi cặp mã dùng một số quan sát khác nhau, ma trận thu được có
    thể không nửa xác định dương và bài toán tối ưu sẽ vô nghiệm.

    Mã không lấy được dữ liệu được loại và báo tên ra ngoài, thay vì làm dừng cả
    trang — người dùng cần biết rổ thực tế được tối ưu gồm những mã nào.
    """
    series, failed = {}, []
    for t in tickers:
        df, src = get_ohlcv(t, days, allow_mock=False)
        if df.empty or len(df) < 30:
            failed.append(t)
        else:
            series[t] = df["close"]
    if not series:
        return pd.DataFrame(), failed
    # Loại phiên khuyết trên GIÁ trước, rồi mới tính lợi suất. Thứ tự ngược lại sẽ
    # tạo ra lợi suất bắc cầu qua các khoảng trống, thổi phồng biến động ước lượng.
    return pd.DataFrame(series).dropna(), failed


def render_risk_optimization_page() -> None:
    setup_page("Risk Optimization", "🛡️")
    page_header("Tối ưu hóa danh mục & kiểm thử rủi ro",
                "Mô hình Markowitz, đường biên hiệu quả giải bằng tối ưu, VaR/CVaR lịch sử")

    tickers = multi_ticker_selector("opt", "Rổ cổ phiếu")
    days = period_selector("opt", 730)
    capital = st.sidebar.number_input("Tổng vốn (VND)", value=500_000_000, step=50_000_000)
    max_w = st.sidebar.slider("Trần tỷ trọng mỗi mã", 0.2, 1.0, 0.4, 0.05,
                              help="Ràng buộc tập trung. 1.0 = không giới hạn.")
    cov_label = st.sidebar.selectbox(
        "Ước lượng hiệp phương sai", list(COV_METHODS), index=1,
        help="Ledoit–Wolf co ma trận mẫu về mục tiêu tương quan hằng số, "
             "làm giảm sai số ước lượng mà bộ tối ưu vốn khuếch đại.")
    sidebar_assumptions()

    prices, failed = load_price_matrix(tuple(tickers), days)
    if failed:
        st.warning(f"Bỏ qua các mã không lấy được dữ liệu: **{', '.join(failed)}**")
    if prices.empty or prices.shape[1] < 2:
        st.error("Cần ít nhất 2 mã có dữ liệu hợp lệ để tối ưu hóa.")
        st.stop()

    returns = prices.apply(log_returns).dropna()
    mean_ret = returns.mean()
    cov, delta = covariance_matrix(returns, COV_METHODS[cov_label])

    n_param = prices.shape[1] * (prices.shape[1] + 1) // 2
    st.caption(f"{prices.shape[1]} mã · {len(returns):,} phiên giao nhau · "
               f"{prices.index[0]:%d/%m/%Y} → {prices.index[-1]:%d/%m/%Y} · "
               f"{n_param} tham số hiệp phương sai ước lượng từ {len(returns):,} quan sát")

    if COV_METHODS[cov_label] == "ledoit_wolf":
        note(f"<b>Hệ số co Ledoit–Wolf: δ = {delta:.3f}.</b> Ma trận dùng để tối ưu là "
             f"<code>Σ* = {delta:.3f}·F + {1 - delta:.3f}·S</code>, trong đó S là hiệp "
             f"phương sai mẫu và F là mục tiêu tương quan hằng số. δ được ước lượng từ "
             f"chính dữ liệu chứ không chọn tay. δ càng gần 1 nghĩa là ma trận mẫu càng "
             f"nhiễu so với số quan sát hiện có, và trọng số tối ưu tính từ S sẽ càng "
             f"không đáng tin ngoài mẫu.")

    # ---------------- Tối ưu ----------------
    w_sharpe = guard_model(Opt.optimize_sharpe, mean_ret, cov, max_weight=max_w)
    w_minvar = guard_model(Opt.optimize_min_variance, mean_ret, cov, max_weight=max_w)
    if w_sharpe is None or w_minvar is None:
        st.stop()

    r_s, v_s, sh_s = Opt.calculate_performance(w_sharpe, mean_ret, cov)
    r_m, v_m, sh_m = Opt.calculate_performance(w_minvar, mean_ret, cov)

    st.markdown("##### 1 · Tỷ trọng tối ưu")
    tbl = pd.DataFrame({
        "Mã": prices.columns,
        "Max Sharpe": [f"{w:.1%}" for w in w_sharpe],
        "Phương sai nhỏ nhất": [f"{w:.1%}" for w in w_minvar],
    })
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.dataframe(tbl, use_container_width=True, hide_index=True)
    with c2:
        k = st.columns(3)
        k[0].metric("Lợi suất kỳ vọng/năm", f"{r_s:+.2%}")
        k[1].metric("Biến động/năm", f"{v_s:.2%}")
        k[2].metric("Sharpe", f"{sh_s:.3f}")
        st.caption(f"Danh mục phương sai nhỏ nhất: lợi suất {r_m:+.2%}, "
                   f"biến động {v_m:.2%}, Sharpe {sh_m:.3f}")

    # ---------------- VaR ----------------
    st.markdown("##### 2 · Rủi ro danh mục Max Sharpe")
    port_ret = (returns * w_sharpe).sum(axis=1)
    var = guard_model(Opt.calculate_var_cvar, port_ret, 0.95, capital)
    if var is not None:
        k = st.columns(4)
        k[0].metric("VaR 95% (1 phiên)", f"-{var['var_amount']/1e6:,.2f} tr",
                    delta=f"-{var['var_pct']:.2%}", delta_color="inverse")
        k[1].metric("CVaR 95% (1 phiên)", f"-{var['cvar_amount']/1e6:,.2f} tr",
                    delta=f"-{var['cvar_pct']:.2%}", delta_color="inverse")
        k[2].metric("VaR tham số (chuẩn)", f"-{var['var_param_pct']:.2%}",
                    help="Giả định phân phối chuẩn. Chênh với VaR lịch sử cho thấy đuôi dày.")
        k[3].metric("Cỡ mẫu / vùng đuôi", f"{var['n_obs']:,} / {var['n_tail']}")

        kup = Opt.kupiec_test(port_ret, var["var_pct"], 0.95)
        pval = f"{kup['pvalue']:.4f}" if kup["pvalue"] == kup["pvalue"] else "không tính được"
        note(f"<b>Hậu kiểm mô hình VaR bằng kiểm định Kupiec (1995).</b> Kiểm định này so "
             f"sánh số lần lợi suất thực tế vượt ngưỡng VaR với số lần lý thuyết. Dưới giả "
             f"thuyết H₀ rằng mô hình VaR được đặc tả đúng, số lần vượt tuân theo phân phối "
             f"nhị thức B(n, 1−c); thống kê tỷ số hợp lý tương ứng tuân theo χ² với 1 bậc "
             f"tự do. Kết quả: <b>{kup['violations']} lần vượt ngưỡng trên {kup['n']} phiên</b> "
             f"so với kỳ vọng lý thuyết {kup['expected']:.1f}, p-value = {pval}. p-value "
             f"&lt; 0,05 dẫn tới bác bỏ H₀ — mô hình ước lượng rủi ro sai lệch một cách hệ "
             f"thống. Cần lưu ý Kupiec chỉ kiểm định <i>tần suất</i> vượt ngưỡng chứ không "
             f"kiểm định tính <i>độc lập</i> của chúng: một mô hình cho đúng số lần vượt "
             f"nhưng dồn cả vào một giai đoạn khủng hoảng vẫn qua được kiểm định này "
             f"(kiểm định Christoffersen bổ sung chiều còn thiếu đó). Ngoài ra, VaR ở đây "
             f"là <b>trong mẫu</b>: trọng số được tối ưu trên chính chuỗi lợi suất dùng để "
             f"đo VaR, nên kết quả lạc quan hơn thực tế một cách có hệ thống.")

    # ---------------- Đường biên ----------------
    st.markdown("##### 3 · Đường biên hiệu quả")
    frontier = guard_model(Opt.efficient_frontier, mean_ret, cov, 40, max_w)
    cloud = Opt.random_portfolios(mean_ret, cov, 1500)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cloud["vol"], y=cloud["ret"], mode="markers",
                             name="Danh mục ngẫu nhiên",
                             marker=dict(size=4, opacity=0.35, color=cloud["sharpe"],
                                         colorscale="Viridis", showscale=True,
                                         colorbar=dict(title="Sharpe"))))
    if frontier is not None:
        fig.add_trace(go.Scatter(x=frontier["vol"], y=frontier["ret"], mode="lines",
                                 name="Đường biên hiệu quả",
                                 line=dict(color=ACCENT, width=3)))
    fig.add_trace(go.Scatter(x=[v_s], y=[r_s], mode="markers", name="Max Sharpe",
                             marker=dict(size=16, color=ACCENT_DOWN, symbol="star")))
    fig.add_trace(go.Scatter(x=[v_m], y=[r_m], mode="markers", name="Phương sai nhỏ nhất",
                             marker=dict(size=13, color=ACCENT_UP, symbol="diamond")))
    fig.update_xaxes(title_text="Biến động năm", tickformat=".1%")
    fig.update_yaxes(title_text="Lợi suất kỳ vọng năm", tickformat=".1%")
    st.plotly_chart(apply_theme(fig, 520), use_container_width=True)

    note("<b>Đường biên hiệu quả theo Markowitz (1952).</b> Đường liền nét được dựng bằng "
         "cách giải một bài toán <b>quy hoạch toàn phương</b> cho từng mức lợi suất mục "
         "tiêu R*: cực tiểu hóa phương sai danh mục wᵀΣw với các ràng buộc Σwᵢ = 1 (đầu tư "
         "toàn bộ vốn), wᵀμ = R* (đạt mức lợi suất yêu cầu) và 0 ≤ wᵢ ≤ trần tỷ trọng "
         "(không bán khống, giới hạn tập trung). Tập nghiệm tạo thành biên trên của tập "
         "khả thi trong không gian trung bình–phương sai; mọi danh mục nằm dưới đường này "
         "đều bị <i>chi phối</i> theo nghĩa có một danh mục khác cùng rủi ro nhưng lợi suất "
         "cao hơn.<br><br>"
         "Đám mây điểm phía sau là các danh mục sinh <b>ngẫu nhiên</b>, chỉ nhằm minh họa "
         "hình dạng tập khả thi — nó <b>không</b> phải đường biên và về mặt xác suất không "
         "thể tiệm cận hai đầu mút. Lý do thuần túy thống kê: trọng số sinh từ phân phối "
         "đều rồi chuẩn hóa về tổng bằng 1 sẽ tuân theo phân phối tập trung quanh danh mục "
         "cân bằng đều; với n = 4 mã, xác suất một trọng số vượt 0,9 chỉ khoảng "
         "<b>0,025%</b>, nên trong 1.500 lần rút gần như chắc chắn không xuất hiện danh "
         "mục tập trung — mà chính các danh mục tập trung mới nằm ở hai đầu đường biên. "
         "Lấy đường bao của đám mây ngẫu nhiên làm đường biên hiệu quả vì vậy sẽ ước lượng "
         "thiếu tập cơ hội đầu tư một cách có hệ thống.<br><br>"
         "<b>Hạn chế của mô hình:</b> μ và Σ ở đây là ước lượng mẫu, không phải tham số "
         "thật. Bài toán tối ưu rất nhạy với sai số ước lượng của μ và có xu hướng dồn "
         "trọng số vào những mã tình cờ có lợi suất lịch sử cao — hiện tượng "
         "<b>Michaud (1989)</b> gọi là “cỗ máy tối đa hóa sai số ước lượng”. Trần tỷ trọng "
         "ở thanh bên là một ràng buộc chính quy hóa nhằm hạn chế đúng vấn đề này.")


if __name__ == "__main__":
    render_risk_optimization_page()
