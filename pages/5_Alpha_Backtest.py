# pages/5_Alpha_Backtest.py — module mở rộng (ngoài 5 yêu cầu của đề)
import plotly.graph_objects as go
import streamlit as st

from core.alpha_engine import SIGNALS, AlphaEngine
from data.dnse_client import get_ohlcv
from ui.charts import apply_theme
from ui.components import (guard_data, guard_model, note, page_header, period_selector,
                           setup_page, sidebar_assumptions, source_badge, ticker_selector)
from utils.config import (ACCENT, ACCENT_DOWN, ACCENT_UP, MUTED, SETTLEMENT_LAG,
                          TRANSACTION_COST)


def render_alpha_page() -> None:
    setup_page("Alpha Backtest", "🧪")
    ticker = ticker_selector("alpha")
    days = period_selector("alpha", 730)
    sidebar_assumptions()

    page_header(f"Kiểm thử tín hiệu Alpha · {ticker}",
                "Backtest vector hóa, có phí giao dịch và ràng buộc vi cấu trúc thị trường Việt Nam")

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        choice = c1.selectbox("Tín hiệu", SIGNALS)
        capital = c2.number_input("Vốn ban đầu (VND)", value=100_000_000, step=10_000_000)
        cost = c3.number_input("Phí mỗi lượt (%)", value=TRANSACTION_COST * 100,
                               step=0.05, format="%.2f") / 100
        allow_short = c4.checkbox("Cho phép bán khống", value=False,
                                  help="TTCK Việt Nam không có bán khống cổ phiếu. "
                                       "Bật để so sánh học thuật, không phải để kết luận.")

    df, source = get_ohlcv(ticker, days)
    guard_data(df, ticker, min_rows=30)
    source_badge(source)

    signal = AlphaEngine.calculate_alpha_signal(df, choice)
    res = guard_model(AlphaEngine.backtest_signal, df, signal,
                      initial_capital=capital, transaction_cost=cost,
                      allow_short=allow_short)
    if res is None:
        return

    k = st.columns(5)
    k[0].metric("Tổng lợi nhuận", f"{res['total_return']:+.2%}",
                delta=f"{res['excess_vs_benchmark']:+.2%} so với mua & giữ")
    k[1].metric("Sharpe Ratio", f"{res['sharpe_ratio']:.2f}",
                help="Sharpe = (R_p − R_f)/σ_p, năm hóa. Tử số là lợi suất VƯỢT TRỘI so "
                     "với lãi suất phi rủi ro. Nếu không trừ R_f, đại lượng thu được là "
                     "một dạng Information Ratio so với mốc 0, không phải Sharpe.")
    k[2].metric("Max Drawdown", f"{res['max_drawdown']:.2%}")
    k[3].metric("Tỷ lệ thắng / LỆNH", f"{res['win_rate']:.1%}",
                help=f"{res['n_trades']} lệnh, giữ trung bình "
                     f"{res['avg_holding_days']:.1f} phiên/lệnh")
    k[4].metric("Tổng phí đã trả", f"{res['total_cost']/1e6:,.1f} tr")

    k = st.columns(4)
    k[0].metric("Lợi nhuận năm hóa", f"{res['ann_return']:+.2%}")
    k[1].metric("Information Ratio", f"{res['information_ratio']:.2f}")
    k[2].metric("Sortino Ratio", f"{res['sortino_ratio']:.2f}"
                if res["sortino_ratio"] == res["sortino_ratio"] else "—")
    k[3].metric("Tổng turnover", f"{res['total_turnover']:.1f}x")

    a = res["assumptions"]
    note(
        f"<b>Giả định đã áp dụng.</b> "
        f"Bán khống: <b>{'CÓ' if a['allow_short'] else 'KHÔNG'}</b> — thị trường Việt Nam "
        f"không cho bán khống cổ phiếu, và tín hiệu Mean-Reversion đối xứng quanh 0 nên nếu "
        f"bật, khoảng một nửa hiệu suất đến từ giao dịch không thực hiện được. "
        f"Độ trễ khớp lệnh: <b>T+{a['execution_lag']}</b> (tín hiệu chốt hết phiên T, khớp "
        f"phiên sau — chống look-ahead bias). "
        f"Thanh toán: <b>T+{a['settlement_lag']}</b> — sau khi mua, vị thế bị giữ tối thiểu "
        f"{a['settlement_lag']} phiên vì cổ phiếu chưa về tài khoản. "
        f"Phí: <b>{a['transaction_cost']:.2%}</b> mỗi lượt, tính trên turnover thực tế."
    )

    data = res["data"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index, y=data["equity"], name="Chiến lược",
                             line=dict(color=ACCENT_UP, width=2)))
    fig.add_trace(go.Scatter(x=data.index, y=capital * data["cum_market_return"],
                             name="Mua và giữ", line=dict(color=ACCENT, dash="dash", width=1.6)))
    fig.update_yaxes(title_text="Giá trị tài sản (VND)")
    st.plotly_chart(apply_theme(fig, 460, "Đường cong tài sản"), use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        eq = data["equity"]
        dd = (eq - eq.cummax()) / eq.cummax()
        fig = go.Figure(go.Scatter(x=data.index, y=dd, fill="tozeroy",
                                   line=dict(color=ACCENT_DOWN, width=1)))
        fig.update_yaxes(title_text="Drawdown", tickformat=".0%")
        st.plotly_chart(apply_theme(fig, 300, "Mức sụt giảm từ đỉnh"), use_container_width=True)
    with c2:
        if len(res["trade_returns"]):
            fig = go.Figure(go.Histogram(x=res["trade_returns"], nbinsx=30,
                                         marker_color=ACCENT, opacity=0.8))
            fig.add_vline(x=0, line_color=MUTED, line_dash="dash")
            fig.update_xaxes(title_text="Lợi nhuận mỗi lệnh", tickformat=".0%")
            st.plotly_chart(apply_theme(fig, 300, "Phân phối lợi nhuận theo LỆNH"),
                            use_container_width=True)
            note("<b>Đơn vị quan sát của tỷ lệ thắng.</b> Histogram này lấy đơn vị quan sát "
                 "là <b>lệnh</b>: mỗi lệnh là một chuỗi phiên liên tiếp giữ cùng chiều vị "
                 "thế, và lợi nhuận lệnh được tính lũy kế từ khi mở đến khi đóng vị thế. "
                 "Cách tính này khác hẳn tỷ lệ ngày lãi trên tổng số ngày nắm giữ, và thường "
                 "cho con số thấp hơn, vì một lệnh thắng kéo dài bị gộp thành một quan sát "
                 "duy nhất thay vì tách thành nhiều ngày lãi. Khi đối chiếu với tài liệu "
                 "hoặc so sánh giữa các chiến lược, đơn vị quan sát phải được nêu rõ, nếu "
                 "không hai con số cùng tên gọi sẽ không so sánh được. Tỷ lệ thắng cũng "
                 "không đủ để đánh giá chiến lược nếu tách khỏi <b>tỷ số lãi/lỗ bình quân</b>: "
                 "một chiến lược thắng 30% số lệnh vẫn có kỳ vọng dương nếu lệnh thắng lớn "
                 "hơn nhiều lần lệnh thua.")

    note("<b>Giới hạn về mặt suy diễn thống kê.</b> Toàn bộ kiểm thử được thực hiện "
         "<i>trong mẫu</i> (in-sample) trên cùng một khoảng dữ liệu, không tách tập huấn "
         "luyện và tập kiểm định. Do tham số tín hiệu được chọn khi đã quan sát được kết "
         "quả, ước lượng hiệu suất chịu <b>sai lệch do khai thác dữ liệu</b> (data-snooping "
         "bias) theo nghĩa của <b>White (2000)</b>: khi thử nhiều biến thể trên cùng một "
         "chuỗi, một vài biến thể sẽ cho kết quả tốt do ngẫu nhiên, và Sharpe quan sát được "
         "là ước lượng chệch lên của Sharpe thật. Kết quả trên vì vậy nên đọc như một phép "
         "mô tả hành vi lịch sử của tín hiệu, <b>không</b> phải bằng chứng về hiệu quả ngoài "
         "mẫu. Kiểm chứng đúng cách đòi hỏi tối thiểu một tập kiểm định giữ riêng, và chặt "
         "chẽ hơn thì dùng walk-forward hoặc hiệu chỉnh đa kiểm định.")


if __name__ == "__main__":
    render_alpha_page()
