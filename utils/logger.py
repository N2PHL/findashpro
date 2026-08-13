# utils/logger.py
"""
Bộ ghi log dùng chung cho toàn ứng dụng.

Lý do tồn tại: các module ở tầng data (dnse_client, yfinance_client) và core
(llm_client) cần báo lỗi ra một nơi CÓ THỂ ĐỌC LẠI, thay vì st.error() — vì lỗi
mạng xảy ra bên trong hàm đã bọc @st.cache_data, nơi việc gọi widget Streamlit là
không hợp lệ. In ra stderr cũng là cách duy nhất để đọc được lỗi trên nhật ký của
Streamlit Cloud (Manage app → Logs).

Ghi log KHÔNG thay thế cho việc báo lỗi cho người dùng: dnse_client vẫn trả về
cờ nguồn dữ liệu ("live" / "mock" / "empty") để tầng UI hiển thị trung thực.
"""
from __future__ import annotations

import logging
import os
import sys

_LEVEL = os.getenv("FINDASH_LOG_LEVEL", "INFO").upper()
_FORMAT = "%(asctime)s │ %(levelname)-7s │ %(name)-12s │ %(message)s"
_DATEFMT = "%H:%M:%S"

_configured: set[str] = set()


def get_logger(name: str) -> logging.Logger:
    """
    Trả về logger đã cấu hình sẵn cho một module.

    Dùng: log = get_logger("dnse")  →  log.warning("API lỗi: %s", exc)

    Handler chỉ được gắn MỘT lần cho mỗi tên. Streamlit chạy lại toàn bộ script
    ở mỗi lần tương tác, nên nếu không chặn thì mỗi lần rerun sẽ cộng thêm một
    handler và cùng một dòng log bị in lặp nhiều lần.
    """
    logger = logging.getLogger(f"findash.{name}")

    if name not in _configured:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATEFMT))
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, _LEVEL, logging.INFO))
        logger.propagate = False          # tránh in lặp qua root logger
        _configured.add(name)

    return logger
