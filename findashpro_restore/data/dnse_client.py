# data/dnse_client.py
"""
Lớp truy cập dữ liệu giá (DNSE / entrade).

Ba quy ước của lớp dữ liệu:
  1. Tên cột được chuẩn hóa về chữ thường ngay tại nguồn, nên toàn bộ tầng phía trên
     dùng chung một schema và không trang nào phải tự đoán cách viết hoa.
  2. Khối lượng khuyết KHÔNG được nội suy tiến (ffill). Khối lượng bằng 0 và khối
     lượng khuyết mang ý nghĩa khác nhau: phiên không có giao dịch là một quan sát
     hợp lệ, còn điền giá trị của phiên trước vào là tạo ra thanh khoản không tồn tại.
  3. get_ohlcv() là điểm truy cập duy nhất dành cho tầng giao diện. Hàm có cache,
     có kiểm tra đầu vào, và luôn trả về DataFrame đúng schema kể cả khi rỗng.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
import streamlit as st

from data.mock_data import generate_ohlcv
from utils.config import is_index as _is_index
from utils.logger import get_logger

log = get_logger("dnse")

BASE_URL = "https://services.entrade.com.vn/chart-api/v2/ohlcs"
OHLCV = ["open", "high", "low", "close", "volume"]

# Quy tắc gộp nến — yêu cầu [2]: lấy mẫu theo ngày/tuần/tháng
_AGG = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
SAMPLING = {"Ngày": None, "Tuần": "W-FRI", "Tháng": "ME", "Quý": "QE"}


def empty_ohlcv() -> pd.DataFrame:
    """DataFrame rỗng NHƯNG ĐÚNG SCHEMA. Đây là thứ chống crash cả app."""
    return pd.DataFrame(columns=OHLCV, index=pd.DatetimeIndex([], name="date"))


def clean_financial_data(df: pd.DataFrame) -> pd.DataFrame:
    """Vệ sinh dữ liệu giá. Mỗi bước dưới đây tương ứng một lỗi đã bị bắt."""
    if df.empty:
        return df

    df = df.replace([np.inf, -np.inf], np.nan)

    # Không có giá đóng cửa thì không tính được gì -> bỏ hàng
    if "close" in df.columns:
        df = df.dropna(subset=["close"])

    # Khối lượng khuyết = phiên không có giao dịch = 0. TUYỆT ĐỐI KHÔNG ffill.
    if "volume" in df.columns:
        df["volume"] = df["volume"].fillna(0.0)

    # OHL khuyết thì suy từ close (nến doji), vẫn tốt hơn là bỏ cả phiên
    for col in ("open", "high", "low"):
        if col in df.columns and "close" in df.columns:
            df[col] = df[col].fillna(df["close"])

    return df.sort_index()


# ---------------------------------------------------------------------------
# CHIA TÁCH / CỔ TỨC — điều chỉnh giá về chuỗi liên tục
# ---------------------------------------------------------------------------
# Endpoint entrade trả GIÁ THÔ, không điều chỉnh sự kiện quyền. Doanh nghiệp Việt
# Nam chia cổ tức bằng cổ phiếu và thưởng rất dày, nên mỗi lần chia tạo ra một cú
# sụt giá KHÔNG PHẢI do thị trường. Nếu để nguyên, cú sụt đó đi thẳng vào chuỗi
# lợi suất: độ lệch chuẩn phồng lên, beta của CAPM méo, và Monte Carlo mô phỏng
# một mức rủi ro không tồn tại.
#
# Cách nhận diện: biên độ dao động một phiên trên HOSE bị chặn ở ±7% (HNX ±10%,
# UPCoM ±15%). Một bước nhảy close-to-close vượt xa ngưỡng đó KHÔNG THỂ là biến
# động giá thông thường — nó là sự kiện quyền. Ngưỡng mặc định 18% nằm trên trần
# biên độ của cả ba sàn nên gần như không bắt nhầm phiên giao dịch thật.
#
# Giới hạn của phương pháp, cần nói rõ khi bảo vệ: đây là suy luận từ chính chuỗi
# giá, KHÔNG phải dữ liệu quyền chính thức từ sở giao dịch. Nó không phân biệt được
# cổ tức tiền mặt lớn với chia tách, và bỏ sót các đợt chia nhỏ dưới ngưỡng. Nguồn
# đúng là bản tin quyền của HOSE hoặc trường điều chỉnh của một nhà cung cấp dữ liệu
# có bản quyền.
SPLIT_THRESHOLD = 0.18


def detect_corporate_actions(df: pd.DataFrame,
                             threshold: float = SPLIT_THRESHOLD) -> pd.DataFrame:
    """
    Liệt kê các phiên nghi có sự kiện quyền (chia tách / cổ tức bằng cổ phiếu).

    Trả về DataFrame các phiên vượt ngưỡng, kèm tỷ lệ điều chỉnh ước lượng
    (giá sau / giá trước). Rỗng nghĩa là chuỗi giá không có dấu hiệu bất thường.
    """
    if df.empty or "close" not in df.columns or len(df) < 2:
        return pd.DataFrame(columns=["gap", "ratio"])

    close = df["close"].astype(float)
    gap = close.pct_change()
    flagged = gap[gap.abs() > threshold]

    return pd.DataFrame({"gap": flagged, "ratio": 1.0 + flagged})


def adjust_for_corporate_actions(df: pd.DataFrame,
                                 threshold: float = SPLIT_THRESHOLD) -> pd.DataFrame:
    """
    Điều chỉnh LÙI giá về chuỗi liên tục (back-adjustment).

    Quy ước chuẩn của ngành: giữ nguyên giá gần nhất và chia ngược các giá TRƯỚC
    sự kiện cho hệ số điều chỉnh. Nhờ vậy mức giá hiện tại vẫn khớp bảng giá thị
    trường, còn chuỗi lợi suất không còn cú sụt giả.

    Khối lượng nhân với cùng hệ số theo chiều ngược lại, để giá × khối lượng
    (giá trị giao dịch) không bị bóp méo.
    """
    actions = detect_corporate_actions(df, threshold)
    if actions.empty:
        return df

    out = df.copy()
    for date, row in actions.iterrows():
        factor = float(row["ratio"])
        if factor <= 0:
            continue
        before = out.index < date
        for col in ("open", "high", "low", "close"):
            if col in out.columns:
                out.loc[before, col] = out.loc[before, col] * factor
        if "volume" in out.columns:
            out.loc[before, "volume"] = out.loc[before, "volume"] / factor

    log.info("Đã điều chỉnh %d sự kiện quyền", len(actions))
    return out


def fetch_historical_data(
    ticker: str,
    start_timestamp: int,
    end_timestamp: int,
    resolution: str = "1D",
    is_index: bool | None = None,
) -> pd.DataFrame:
    """Gọi API thô. Trả về OHLCV chữ thường, index là DatetimeIndex tên 'date'."""
    ticker = ticker.strip().upper()
    if is_index is None:
        is_index = _is_index(ticker)

    url = f"{BASE_URL}/{'index' if is_index else 'stock'}"
    params = {
        "symbol": ticker,
        "from": start_timestamp,
        "to": end_timestamp,
        "resolution": resolution,
    }

    try:
        r = requests.get(url, params=params, timeout=10,
                         headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        payload = r.json()

        if not payload or "t" not in payload or not payload["t"]:
            log.warning("API không trả dữ liệu cho %s", ticker)
            return empty_ohlcv()

        n = len(payload["t"])
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(payload["t"], unit="s"),
                "open": payload.get("o", [np.nan] * n),
                "high": payload.get("h", [np.nan] * n),
                "low": payload.get("l", [np.nan] * n),
                "close": payload.get("c", [np.nan] * n),
                "volume": payload.get("v") or [0.0] * n,
            }
        )
        df["date"] = df["date"].dt.normalize()
        df = df.set_index("date")
        return clean_financial_data(df)

    except Exception as exc:                      # noqa: BLE001
        log.error("Lỗi lấy dữ liệu %s: %s", ticker, exc)
        return empty_ohlcv()


@st.cache_data(ttl=300, show_spinner=False)
def get_ohlcv(
    ticker: str,
    days: int = 365,
    resolution: str = "1D",
    min_rows: int = 2,
    allow_mock: bool = True,
    adjust: bool = True,
) -> tuple[pd.DataFrame, str]:
    """
    Hàm DUY NHẤT mà tầng UI được phép gọi.

    Trả về (df, nguồn) với nguồn ∈ {"live", "mock", "empty"}.
    Luôn có đủ 5 cột OHLCV kể cả khi rỗng -> mọi phép .columns, ['close'] đều an toàn.

    adjust=True điều chỉnh lùi giá qua các sự kiện quyền nghi ngờ (xem
    adjust_for_corporate_actions). Đặt False khi cần xem đúng giá thô đã niêm yết.
    """
    ticker = ticker.strip().upper()
    if not ticker:
        return empty_ohlcv(), "empty"

    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=days)).timestamp())

    df = fetch_historical_data(ticker, start_ts, end_ts, resolution=resolution)

    if not df.empty and len(df) >= min_rows:
        if adjust:
            df = adjust_for_corporate_actions(df)
        return df, "live"

    if allow_mock:
        log.warning("Chuyển sang dữ liệu mô phỏng cho %s", ticker)
        return generate_ohlcv(ticker, days), "mock"

    return empty_ohlcv(), "empty"


def resample_ohlcv(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """
    Lấy mẫu theo Ngày/Tuần/Tháng/Quý (yêu cầu [2]).

    Gộp phía client thay vì gửi resolution='1W' lên API, vì chart-api/v2 không cam kết
    hỗ trợ khung tuần/tháng. Gộp ở đây cũng cho phép kiểm soát minh bạch quy tắc OHLCV:
    open = giá mở cửa phiên ĐẦU kỳ, high/low = max/min cả kỳ, close = phiên CUỐI kỳ,
    volume = TỔNG (không phải trung bình).
    """
    rule = SAMPLING.get(label)
    if rule is None or df.empty:
        return df
    agg = {k: v for k, v in _AGG.items() if k in df.columns}
    return df.resample(rule).agg(agg).dropna(subset=["close"])
