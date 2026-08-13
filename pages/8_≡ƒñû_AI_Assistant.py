# pages/8_🤖_AI_Assistant.py — module mở rộng (ngoài 5 yêu cầu của đề)
import streamlit as st

from core.llm_client import build_context, get_ai_response
from core.quantitative import describe_returns
from data.dnse_client import get_ohlcv
from ui.components import (note, page_header, setup_page, sidebar_assumptions, ticker_selector)


@st.cache_data(ttl=300, show_spinner=False)
def build_snapshot(ticker: str) -> dict:
    """
    Dựng khối số liệu thực tế của mã đang chọn để đưa vào ngữ cảnh gửi cho mô hình.

    Mô hình ngôn ngữ không truy cập được dữ liệu thị trường; mọi con số nó nêu ra
    mà không có trong khối ngữ cảnh này đều là nội dung sinh từ tham số huấn luyện,
    không phải quan sát. Việc nạp tường minh giá, biên độ và thống kê mô tả là cách
    ràng buộc câu trả lời vào dữ liệu kiểm chứng được.
    """
    df, source = get_ohlcv(ticker, 365)
    if df.empty:
        return {}
    snap = {
        "Giá đóng cửa gần nhất": f"{df['close'].iloc[-1]:,.2f}",
        "Phiên gần nhất": f"{df.index[-1]:%d/%m/%Y}",
        "Đỉnh 52 tuần": f"{df['high'].tail(252).max():,.2f}",
        "Đáy 52 tuần": f"{df['low'].tail(252).min():,.2f}",
        "Khối lượng TB 20 phiên": f"{df['volume'].tail(20).mean():,.0f}",
        "Nguồn dữ liệu": "trực tiếp" if source == "live" else "MÔ PHỎNG (API lỗi)",
    }
    try:
        for _, row in describe_returns(df["close"]).iterrows():
            snap[row["Chỉ tiêu"]] = row["Giá trị"]
    except ValueError:
        pass
    return snap


def render_chat_page() -> None:
    setup_page("AI Assistant", "🤖")
    ticker = ticker_selector("ai")
    sidebar_assumptions()

    page_header(f"Trợ lý định lượng · {ticker}",
                "Hỏi đáp về phương pháp, có nạp số liệu thật của mã đang chọn vào ngữ cảnh")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    snapshot = build_snapshot(ticker)
    with st.expander(f"Ngữ cảnh đang gửi kèm cho mô hình ({len(snapshot)} trường)"):
        if snapshot:
            st.json(snapshot)
        else:
            st.caption("Chưa tải được số liệu — trợ lý sẽ chỉ trả lời ở mức phương pháp chung.")

    note("<b>Phạm vi và giới hạn của trợ lý.</b> Mô hình ngôn ngữ được truy cập qua API "
         "Groq, <b>không</b> truy cập internet và <b>không</b> đọc tin tức. Toàn bộ dữ liệu "
         "thị trường mà nó có là khối ngữ cảnh hiển thị phía trên; bất kỳ con số nào xuất "
         "hiện trong câu trả lời mà không truy nguyên được về khối đó đều phải coi là nội "
         "dung sinh ra từ tham số mô hình chứ không phải quan sát thực nghiệm, và cần kiểm "
         "chứng lại trước khi sử dụng. Trợ lý phù hợp cho câu hỏi về <i>phương pháp</i> — "
         "giả định của CAPM, cách đọc VaR, khác biệt giữa GBM và Bootstrap — hơn là cho "
         "câu hỏi đòi hỏi số liệu mới.")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input(f"Hỏi về {ticker}, CAPM, APT, VaR, Monte Carlo…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"), st.spinner("Đang xử lý…"):
            answer, ok = get_ai_response(st.session_state.messages,
                                         build_context(ticker, snapshot))
            st.markdown(answer)

        # Chỉ lưu câu trả lời thành công vào lịch sử. Nếu lưu cả thông báo lỗi API,
        # chuỗi lỗi đó sẽ được gửi lại như một lượt hội thoại hợp lệ ở lần sau.
        if ok:
            st.session_state.messages.append({"role": "assistant", "content": answer})
        else:
            st.session_state.messages.pop()

    if st.session_state.messages and st.sidebar.button("Xóa lịch sử trò chuyện"):
        st.session_state.messages = []


if __name__ == "__main__":
    render_chat_page()
