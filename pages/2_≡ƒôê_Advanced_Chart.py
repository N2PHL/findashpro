# pages/2_📈_Advanced_Chart.py — yêu cầu [2]: biến động giá/khối lượng, LẤY MẪU, dạng biểu đồ
import plotly.graph_objects as go
import streamlit as st

from core.indicators import calculate_bollinger, calculate_ema, calculate_rsi, calculate_sma
from data.dnse_client import SAMPLING, get_ohlcv, resample_ohlcv
from ui.charts import apply_theme, create_price_volume_chart
from ui.components import (guard_data, note, page_header, period_selector,
                           setup_page, sidebar_assumptions, source_badge, ticker_selector)
from utils.config import ACCENT, MUTED


def render_advanced_chart() -> None:
    setup_page("Advanced Chart", "📈")
    ticker = ticker_selector("chart")
    days = period_selector("chart", 365)
    sidebar_assumptions()

    page_header(f"Biểu đồ kỹ thuật · {ticker}",
                "Đa khung lấy mẫu, ba dạng biểu đồ và các chỉ báo chồng lớp")

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        freq = c1.selectbox("Lấy mẫu", list(SAMPLING), index=0,
                            help="Dữ liệu ngày được gộp phía ứng dụng theo quy tắc OHLCV")
        plot_type = c2.selectbox("Dạng biểu đồ", ["Candle", "Line", "OHLC"])
        ma_window = c3.number_input("Chu kỳ MA", min_value=5, max_value=200, value=20, step=5)
        overlay_choice = c4.multiselect("Chỉ báo", ["SMA", "EMA", "Bollinger", "RSI"],
                                        default=["SMA"])

    with st.spinner(f"Đang tải dữ liệu {ticker}…"):
        df_daily, source = get_ohlcv(ticker, days)
    guard_data(df_daily, ticker, min_rows=2)
    source_badge(source)

    # Lấy mẫu TRƯỚC khi tính chỉ báo: MA 20 trên dữ liệu tuần là 20 TUẦN, không phải 20 ngày
    df = resample_ohlcv(df_daily, freq)
    unit = {"Ngày": "phiên", "Tuần": "tuần", "Tháng": "tháng", "Quý": "quý"}[freq]
    guard_data(df, ticker, min_rows=2)

    if len(df) < ma_window:
        note(f"Chu kỳ MA ({ma_window}) <b>lớn hơn số quan sát sau khi lấy mẫu</b> "
             f"({len(df)} {unit}). Đường trung bình sẽ rỗng — hãy giảm chu kỳ hoặc "
             f"nới rộng khoảng thời gian.")

    overlays = {}
    if "SMA" in overlay_choice:
        overlays[f"SMA {ma_window} {unit}"] = calculate_sma(df, ma_window, "close")
    if "EMA" in overlay_choice:
        overlays[f"EMA {ma_window} {unit}"] = calculate_ema(df, ma_window, "close")
    if "Bollinger" in overlay_choice:
        up, mid, lo = calculate_bollinger(df["close"], min(20, max(len(df) - 1, 2)))
        overlays["Bollinger trên"] = up
        overlays["Bollinger dưới"] = lo

    st.plotly_chart(create_price_volume_chart(df, ticker, plot_type, overlays),
                    use_container_width=True)

    if "RSI" in overlay_choice:
        st.markdown("##### RSI (14)")
        rsi = calculate_rsi(df["close"], 14)
        fig = go.Figure(go.Scatter(x=df.index, y=rsi, mode="lines", name="RSI",
                                   line=dict(color=ACCENT, width=1.5)))
        for lvl, txt in ((70, "Ngưỡng 70 — vùng quá mua theo quy ước Wilder"),
                         (30, "Ngưỡng 30 — vùng quá bán theo quy ước Wilder")):
            fig.add_hline(y=lvl, line_dash="dot", line_color=MUTED,
                          opacity=0.6, annotation_text=txt)
        fig.update_yaxes(range=[0, 100])
        st.plotly_chart(apply_theme(fig, 260), use_container_width=True)
        note("<b>Chỉ số sức mạnh tương đối (RSI).</b> RSI = 100 − 100/(1 + RS), trong đó "
             "RS là tỷ số giữa trung bình các mức tăng và trung bình các mức giảm. Trung "
             "bình ở đây theo phương pháp làm mượt lũy thừa của <b>Wilder (1978)</b> với "
             "hệ số α = 1/14, tức mỗi quan sát mới nhận trọng số α còn toàn bộ lịch sử "
             "trước đó nhận trọng số (1 − α) — khác với trung bình động đơn giản, nơi "
             "quan sát rời khỏi cửa sổ thì mất hoàn toàn ảnh hưởng. Hai ngưỡng 70/30 là "
             "<b>quy ước</b> do Wilder đề xuất, không phải giá trị tới hạn rút ra từ kiểm "
             "định thống kê; trong pha xu hướng mạnh, RSI có thể duy trì trên 70 kéo dài "
             "mà giá vẫn tiếp tục tăng, nên đọc RSI tách rời khỏi bối cảnh xu hướng dễ "
             "dẫn tới kết luận sai.")

    note(f"<b>Quy tắc lấy mẫu lại (resampling) chuỗi OHLCV.</b> Đang hiển thị "
         f"<b>{len(df):,} {unit}</b> tổng hợp từ {len(df_daily):,} phiên giao dịch. Trong "
         f"mỗi kỳ: <i>open</i> lấy giá mở cửa của phiên đầu kỳ, <i>high</i> và <i>low</i> "
         f"lấy cực trị của toàn kỳ, <i>close</i> lấy giá đóng cửa của phiên cuối kỳ, còn "
         f"<i>volume</i> là <b>tổng</b> khối lượng — bốn biến giá là thống kê thứ tự nên "
         f"không được lấy trung bình, riêng khối lượng là biến cộng tính nên phải cộng dồn. "
         f"Việc lấy mẫu được thực hiện <b>trước</b> khi tính chỉ báo, do đó đường trung "
         f"bình chu kỳ {ma_window} trên khung này là trung bình của {ma_window} {unit} chứ "
         f"không phải {ma_window} phiên. Đảo thứ tự hai bước sẽ cho ra một chỉ báo khác "
         f"hẳn về tần số cắt (cut-off frequency), dù cùng mang tên gọi.")


if __name__ == "__main__":
    render_advanced_chart()
