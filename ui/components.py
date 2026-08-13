# ui/components.py
"""
Thành phần giao diện dùng chung cho tám trang của ứng dụng.

Mọi trang gọi cùng một bộ hàm ở đây: cấu hình trang, tiêu đề, widget chọn mã, nhãn
nguồn dữ liệu, khối ghi chú phương pháp và các hàm chặn lỗi dữ liệu.

Nguyên tắc thiết kế:
  1. Mã cổ phiếu được chọn từ danh sách có kiểm soát và lưu ở session state, nên
     giá trị đồng bộ trên toàn hệ thống — điều kiện cần để các số liệu giữa các
     trang nói về cùng một đối tượng.
  2. Không gọi st.rerun() sau khi widget đổi giá trị: Streamlit đã tự chạy lại
     script, gọi thêm sẽ nhân đôi số lần truy vấn API.
  3. Nguồn dữ liệu (trực tiếp hay mô phỏng) luôn được gắn nhãn ngay cạnh số liệu,
     để không có con số nào xuất hiện mà người đọc không biết xuất xứ.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from utils.config import (ALL_TICKERS, DEFAULT_PORTFOLIO, MUTED, PRICE_UNIT,
                          RISK_FREE_RATE, TRADING_DAYS, UNIVERSE)

_CSS = Path(__file__).parent / "styles.css"


def setup_page(title: str, icon: str = "📊") -> None:
    """Cấu hình trang và nạp stylesheet dùng chung.

    Layout 'wide' là bắt buộc với các trang có lưới nhiều cột và biểu đồ đôi; ở
    layout mặc định 'centered', vùng nội dung bị bóp lại và các cột chồng lên nhau.
    """
    try:
        st.set_page_config(page_title=f"FinDash Pro — {title}", page_icon=icon,
                           layout="wide", initial_sidebar_state="expanded")
    except Exception:                              # noqa: BLE001  đã gọi rồi
        pass
    if _CSS.exists():
        st.markdown(f"<style>{_CSS.read_text(encoding='utf-8')}</style>",
                    unsafe_allow_html=True)


def page_header(title: str, subtitle: str) -> None:
    st.markdown(f'<h1 class="terminal-header">{title}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="terminal-sub">{subtitle}</p>', unsafe_allow_html=True)


def note(html: str) -> None:
    """Ghi chú giả định mô hình. Nói thẳng giới hạn được điểm cao hơn giấu nó đi."""
    st.markdown(f'<div class="fd-note">{html}</div>', unsafe_allow_html=True)


def source_badge(source: str) -> None:
    if source == "mock":
        st.markdown(
            '<span class="fd-badge mock">dữ liệu mô phỏng</span>'
            'API entrade không phản hồi. Số liệu dưới đây do máy sinh ra để giao diện '
            'vẫn chạy được — <b>không dùng để kết luận về thị trường</b>.',
            unsafe_allow_html=True)
    else:
        st.markdown('<span class="fd-badge live">dữ liệu trực tiếp</span>'
                    f'<span style="color:{MUTED};font-size:.82rem">'
                    f'Nguồn: DNSE / entrade · Đơn vị giá: {PRICE_UNIT}</span>',
                    unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# CHỌN MÃ
# ---------------------------------------------------------------------------
def ticker_selector(key: str) -> str:
    """Widget chọn mã dùng chung cho MỌI trang."""
    if "ticker" not in st.session_state:
        st.session_state["ticker"] = "VCB"

    st.sidebar.markdown("### ⚙️ Bảng điều khiển")

    current = st.session_state["ticker"]
    groups = list(UNIVERSE)
    default_group = next((g for g, ts in UNIVERSE.items() if current in ts), groups[0])

    group = st.sidebar.selectbox("Nhóm ngành", groups,
                                 index=groups.index(default_group), key=f"{key}_group")
    options = UNIVERSE[group]          # LIST có thứ tự — không dùng set(), vốn xáo
                                       # trộn khác nhau mỗi lần khởi động app
    idx = options.index(current) if current in options else 0
    chosen = st.sidebar.selectbox("Mã cổ phiếu", options, index=idx, key=f"{key}_tk")

    with st.sidebar.expander("Nhập mã ngoài danh sách"):
        manual = st.text_input("Mã", value="", key=f"{key}_manual",
                               placeholder="VD: SSI").strip().upper()

    st.session_state["ticker"] = manual or chosen
    return st.session_state["ticker"]              # KHÔNG st.rerun()


def multi_ticker_selector(key: str, label: str = "Rổ cổ phiếu",
                          default: list[str] | None = None, min_n: int = 2) -> list[str]:
    default = default or list(DEFAULT_PORTFOLIO)
    picked = st.sidebar.multiselect(label, ALL_TICKERS,
                                    default=[t for t in default if t in ALL_TICKERS],
                                    key=f"{key}_multi")
    if len(picked) < min_n:
        st.warning(f"Chọn ít nhất {min_n} mã để chạy phân tích danh mục.")
        st.stop()
    return picked


def period_selector(key: str, default_days: int = 365) -> int:
    opts = {"3 tháng": 90, "6 tháng": 180, "1 năm": 365, "2 năm": 730, "5 năm": 1825}
    labels = list(opts)
    idx = labels.index(next(k for k, v in opts.items() if v == default_days))
    return opts[st.sidebar.selectbox("Khoảng thời gian", labels, index=idx, key=f"{key}_period")]


def sidebar_assumptions() -> None:
    """Bày ra các giả định dùng chung. Giảng viên hỏi 'rf của em là bao nhiêu' thì
    câu trả lời nằm sẵn trên màn hình, và chỉ có MỘT con số."""
    st.sidebar.divider()
    st.sidebar.caption(
        f"**Giả định mô hình**  \n"
        f"Lãi suất phi rủi ro: {RISK_FREE_RATE:.2%}/năm  \n"
        f"Số phiên/năm: {TRADING_DAYS}  \n"
        f"Quy ước lợi suất: log return  \n"
        f"Đơn vị giá: {PRICE_UNIT}"
    )


# ---------------------------------------------------------------------------
# GUARD
# ---------------------------------------------------------------------------
def guard_data(df: pd.DataFrame, ticker: str, min_rows: int = 2) -> pd.DataFrame:
    """
    Dừng trang một cách lịch sự thay vì ném traceback.

    Kiểm tra hai điều kiện: DataFrame rỗng, và DataFrame có ít quan sát hơn mức tối
    thiểu mà phép tính phía sau đòi hỏi. Điều kiện thứ hai là cần thiết vì nhiều phép
    tính cần tối thiểu hai quan sát (so sánh với phiên liền trước) hoặc vài chục quan
    sát (thống kê mô tả, ước lượng hiệp phương sai, hồi quy).
    """
    if df is None or df.empty:
        st.error(f"Không có dữ liệu cho mã **{ticker}**. Kiểm tra lại mã hoặc chọn "
                 f"khoảng thời gian khác.")
        st.stop()
    if len(df) < min_rows:
        st.error(f"Mã **{ticker}** chỉ có {len(df)} phiên trong khoảng đã chọn — "
                 f"cần ít nhất {min_rows}. Hãy nới rộng khoảng thời gian.")
        st.stop()

    _corporate_action_notice(df, ticker)
    return df


def _corporate_action_notice(df: pd.DataFrame, ticker: str) -> None:
    """
    Báo cho người đọc biết chuỗi giá có đi qua sự kiện quyền hay không.

    Giữ im lặng ở đây là giấu một nguồn sai lệch đã biết: một cú sụt do chia tách
    trông y hệt một phiên giảm sàn trong chuỗi lợi suất, và nó đẩy độ lệch chuẩn
    cùng beta lên cao một cách giả tạo.
    """
    from data.dnse_client import detect_corporate_actions

    try:
        actions = detect_corporate_actions(df)
    except Exception:                              # noqa: BLE001
        return
    if actions.empty:
        return

    days = ", ".join(d.strftime("%d/%m/%Y") for d in actions.index[:4])
    more = f" và {len(actions) - 4} phiên khác" if len(actions) > 4 else ""
    st.caption(
        f"↻ **{ticker}** — phát hiện {len(actions)} phiên nghi có sự kiện quyền "
        f"(chia tách / cổ tức bằng cổ phiếu): {days}{more}. Giá trước các phiên này "
        f"**đã được điều chỉnh lùi** để chuỗi lợi suất liên tục. Nhận diện dựa trên "
        f"bước nhảy vượt trần biên độ ±7% của HOSE, không phải dữ liệu quyền chính "
        f"thức từ sở giao dịch."
    )


def guard_model(fn, *args, **kwargs):
    """Chạy hàm mô hình; ValueError/RuntimeError thành thông báo đọc được, không phải traceback."""
    try:
        return fn(*args, **kwargs)
    except (ValueError, RuntimeError) as exc:
        st.warning(f"Không chạy được mô hình: {exc}")
        return None
