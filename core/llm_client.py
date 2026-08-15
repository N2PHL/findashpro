# core/llm_client.py
"""
Trợ lý AI (Groq).

Hai nguyên tắc của module:
  1. Mô hình ngôn ngữ không truy cập được dữ liệu thị trường, nên số liệu phải được
     nạp tường minh qua tham số `context` vào system prompt. Nếu không, mọi con số
     xuất hiện trong câu trả lời đều sinh từ tham số huấn luyện chứ không phải quan
     sát — một dạng bịa dữ liệu khó phát hiện vì câu trả lời vẫn trôi chảy.
  2. Hàm trả về kèm cờ trạng thái, để tầng giao diện phân biệt được câu trả lời hợp
     lệ với thông báo lỗi API và không lưu lỗi vào lịch sử hội thoại.
"""
from __future__ import annotations

import os

import streamlit as st

from utils.logger import get_logger

log = get_logger("llm")

MODEL = "openai/gpt-oss-120b"

# ============================================================================
# KHÓA API — KHÔNG BAO GIỜ ĐẶT TRONG MÃ NGUỒN
# ----------------------------------------------------------------------------
# Khóa nằm trong file .py sẽ đi lên GitHub cùng mọi commit. GitHub quét khóa tự
# động và Groq thu hồi khóa bị lộ, thường trong vài phút — nghĩa là trang trợ lý
# sẽ chết đúng vào lúc không mong muốn nhất. Xóa khóa khỏi commit sau đó cũng
# không cứu được: khóa vẫn nằm trong lịch sử Git và vẫn đã bị thu hồi.
#
# Khóa được đọc theo thứ tự: st.secrets -> biến môi trường. Không có đường thứ ba.
#
#   Chạy tại máy       : tạo .streamlit/secrets.toml (đã nằm trong .gitignore)
#                        GROQ_API_KEY = "gsk_..."
#   Streamlit Cloud    : Manage app -> Settings -> Secrets, dán đúng dòng trên
#   Lấy khóa mới       : console.groq.com/keys
#
# Không cấu hình khóa thì bảy trang còn lại vẫn chạy bình thường; chỉ riêng trang
# trợ lý AI hiện hướng dẫn cấu hình thay vì báo lỗi.
# ============================================================================

SYSTEM_PROMPT = """Bạn là chuyên gia phân tích định lượng (Quant Analyst) hỗ trợ sinh viên
làm đồ án Financial Dashboard về thị trường chứng khoán Việt Nam.

QUY ĐỊNH:
- Luôn trả lời bằng TIẾNG VIỆT. Chỉ giữ tiếng Anh cho thuật ngữ (Sharpe Ratio, CAPM, APT, VaR...).
- Ngắn gọn, có cấu trúc, dựa trên dữ liệu.
- Nếu số liệu trong phần NGỮ CẢNH dưới đây không đủ để trả lời, hãy nói thẳng là
  không đủ dữ liệu thay vì suy đoán.
- Không đưa ra khuyến nghị mua/bán cụ thể. Giải thích phương pháp và ý nghĩa con số.
"""


def build_context(ticker: str, snapshot: dict | None = None) -> str:
    """Đóng gói số liệu thật của mã đang chọn thành đoạn ngữ cảnh cho model."""
    if not snapshot:
        return f"NGỮ CẢNH: người dùng đang xem mã {ticker}. Chưa tải được số liệu."
    lines = [f"NGỮ CẢNH — số liệu thật của mã {ticker}:"]
    lines += [f"- {k}: {v}" for k, v in snapshot.items()]
    return "\n".join(lines)


def _read_api_key() -> str:
    """
    Đọc khóa API: st.secrets trước, rồi biến môi trường. Trả về chuỗi rỗng nếu
    không tìm thấy — hàm gọi có trách nhiệm hiển thị hướng dẫn cấu hình.

    st.secrets đọc từ .streamlit/secrets.toml khi chạy tại máy (file đó nằm trong
    .gitignore) và từ mục Secrets của Streamlit Cloud khi deploy. Cùng một dòng
    cấu hình dùng được cho cả hai môi trường.
    """
    try:
        key = str(st.secrets.get("GROQ_API_KEY", "")).strip()
        if key:
            return key
    except Exception:                              # noqa: BLE001  chưa có file secrets
        pass
    return os.environ.get("GROQ_API_KEY", "").strip()


def get_ai_response(messages: list, context: str = "") -> tuple[str, bool]:
    """
    Trả về (nội dung, thành công).

    Cờ `thành công` để trang UI không lưu chuỗi lỗi vào lịch sử chat. Nếu lưu
    thông báo lỗi như một câu trả lời của assistant rồi gửi lại cho model ở lượt
    sau, làm bẩn ngữ cảnh hội thoại.
    """
    try:
        from groq import Groq
    except ImportError:
        return "Chưa cài thư viện `groq`. Chạy: pip install groq", False

    api_key = _read_api_key()
    if not api_key:
        return (
            "**Chưa cấu hình GROQ_API_KEY.**\n\n"
            "Chạy tại máy: tạo file `.streamlit/secrets.toml` (đã được .gitignore bỏ qua) "
            'với nội dung `GROQ_API_KEY = "gsk_..."`.\n\n'
            "Chạy trên Streamlit Cloud: dán cùng dòng đó vào mục Settings → Secrets của app. "
            "Không đặt khóa trực tiếp trong mã nguồn."
        ), False

    payload = [{"role": "system", "content": SYSTEM_PROMPT + "\n\n" + context}]
    payload += [{"role": m["role"], "content": m["content"]} for m in messages]

    try:
        completion = Groq(api_key=api_key).chat.completions.create(
            messages=payload, model=MODEL, temperature=0.2, max_tokens=2048,
        )
        return completion.choices[0].message.content, True
    except Exception as exc:                       # noqa: BLE001
        # Không đưa nội dung khóa vào log hay vào thông báo lỗi hiển thị cho người dùng.
        kind = type(exc).__name__
        log.error("Groq API: %s", kind)
        blob = f"{kind} {exc}".lower()

        # Kiểm tra lỗi MẠNG trước lỗi xác thực. Proxy và tường lửa doanh nghiệp
        # thường trả về 403/PermissionDenied, dễ bị nhận nhầm thành khóa sai và
        # khiến người dùng đi tạo khóa mới trong khi vấn đề nằm ở kết nối.
        if any(w in blob for w in ("allowlist", "egress", "host not in", "proxy",
                                   "connection", "timeout", "apiconnection",
                                   "ssl", "certificate", "getaddrinfo")):
            return ("Không kết nối được tới `api.groq.com`. Kiểm tra mạng; nếu đang dùng "
                    "mạng công ty hoặc trường học thì tên miền này có thể bị chặn."), False

        if any(w in blob for w in ("invalid api key", "invalid_api_key", "authentication",
                                   "401", "unauthorized")):
            return ("**Khóa GROQ_API_KEY không hợp lệ hoặc đã bị thu hồi.** Tạo khóa mới tại "
                    "console.groq.com/keys, rồi cập nhật `.streamlit/secrets.toml` (khi chạy "
                    "tại máy) hoặc mục Settings → Secrets của app (khi chạy trên Streamlit "
                    "Cloud). Nhớ khởi động lại app sau khi đổi khóa."), False
        if any(w in blob for w in ("ratelimit", "rate_limit", "429")):
            return ("Đã chạm giới hạn tần suất của Groq. Chờ vài phút rồi thử lại; nếu lặp "
                    "lại thường xuyên thì cần nâng hạn mức tài khoản."), False
        if any(w in blob for w in ("notfound", "404", "does not exist", "decommission")):
            return (f"Mô hình `{MODEL}` không khả dụng với tài khoản này hoặc đã ngừng phục "
                    f"vụ. Kiểm tra danh sách mô hình hiện hành tại console.groq.com."), False
        if any(w in blob for w in ("permissiondenied", "403", "forbidden")):
            return ("Groq từ chối yêu cầu (403). Nguyên nhân thường gặp: khóa đã bị thu hồi, "
                    "tài khoản chưa kích hoạt, hoặc mạng đang chặn `api.groq.com`."), False
        return f"Không gọi được Groq API ({kind}). Xem log ứng dụng để biết chi tiết.", False
