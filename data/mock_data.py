# data/mock_data.py
"""
Dữ liệu OHLCV mô phỏng — lớp dự phòng khi API entrade không phản hồi.

Vì sao cần: endpoint services.entrade.com.vn/chart-api/v2 là API nội bộ, không có
tài liệu công khai và không có cam kết ổn định. Nếu nó đổi hoặc chặn đúng hôm bảo
vệ, toàn bộ ứng dụng sẽ trắng màn hình. Module này bảo đảm mọi trang vẫn chạy
được và mọi mô hình vẫn tính ra số — với một nhãn "MÔ PHỎNG" hiển thị rõ ràng
trên giao diện, KHÔNG bao giờ trình bày như dữ liệu thật.

Bốn quy ước:

  (a) Tái lập được: seed suy ra từ chính mã cổ phiếu (CRC32, không dùng hash()
      của Python vì hàm đó bị ngẫu nhiên hóa giữa các tiến trình). Cùng một mã
      luôn cho cùng một chuỗi giá, ở mọi lần chạy và mọi máy.
  (b) CÓ tương quan thị trường: mỗi mã = β · nhân tố thị trường chung + phần
      riêng. Nếu sinh độc lập thì β của CAPM ≈ 0 và R² ≈ 0, mô hình trông như
      bị hỏng. Nhân tố chung dùng seed cố định nên mọi mã chia sẻ đúng một
      chuỗi thị trường.
  (c) Cùng một lịch phiên: mọi mã dùng chung chỉ mục ngày làm việc, để
      pd.DataFrame({t: ...}).dropna() không cắt mất dữ liệu.
  (d) Schema khớp tuyệt đối với dnse_client: chỉ mục là ngày, đúng 5 cột chữ
      thường open/high/low/close/volume, đơn vị giá nghìn VND.
"""
from __future__ import annotations

import zlib

import numpy as np
import pandas as pd

from utils.config import RANDOM_SEED, TRADING_DAYS, is_index

# Giá tham chiếu (nghìn VND) — chỉ để con số trông hợp lý trên giao diện.
_BASE_PRICE: dict[str, float] = {
    "VCB": 92.0, "TCB": 24.0, "MBB": 24.5, "ACB": 25.5, "CTG": 36.0,
    "BID": 47.0, "VPB": 19.5, "STB": 34.0,
    "VIC": 42.0, "VHM": 41.0, "VRE": 18.0, "NVL": 11.0, "KDH": 33.0,
    "DXG": 15.5, "PDR": 19.0,
    "HPG": 27.0, "VNM": 66.0, "MSN": 74.0, "SAB": 51.0, "DHG": 105.0,
    "GVR": 33.0, "HSG": 19.0,
    "FPT": 128.0, "MWG": 63.0, "PNJ": 96.0, "CMG": 41.0, "DGW": 45.0,
    "GAS": 68.0, "PLX": 39.0, "POW": 13.0, "PVD": 26.0, "REE": 66.0,
    "VNINDEX": 1265.0, "VN30": 1340.0, "HNXINDEX": 232.0,
}

# Biến động năm hóa giả định theo nhóm
_VOL_INDEX = 0.16
_VOL_STOCK = 0.32

_MARKET_MU = 0.08 / TRADING_DAYS          # drift thị trường 8%/năm
_MARKET_VOL = _VOL_INDEX / np.sqrt(TRADING_DAYS)


def _seed_of(ticker: str) -> int:
    """Seed ổn định giữa các tiến trình — hash() của Python thì không."""
    return zlib.crc32(ticker.upper().encode()) % (2**31)


def _market_factor(n: int) -> np.ndarray:
    """Chuỗi log return của thị trường, dùng chung cho MỌI mã."""
    rng = np.random.default_rng(RANDOM_SEED)
    return _MARKET_MU + _MARKET_VOL * rng.standard_normal(n)


def generate_ohlcv(ticker: str, days: int = 365) -> pd.DataFrame:
    """
    Sinh chuỗi OHLCV mô phỏng cho một mã.

    days là số ngày LỊCH (giống tham số của get_ohlcv); số phiên trả về ít hơn
    vì đã bỏ thứ Bảy và Chủ nhật.

    Trả về DataFrame chỉ mục ngày, đúng 5 cột open/high/low/close/volume.
    """
    ticker = ticker.strip().upper()

    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=max(int(days * 5 / 7), 30))
    n = len(dates)

    idx = is_index(ticker)
    s0 = _BASE_PRICE.get(ticker, 1200.0 if idx else 40.0)

    rm = _market_factor(n)

    if idx:
        # Chỉ số CHÍNH LÀ nhân tố thị trường (VN30 lệch nhẹ so với VNINDEX)
        beta, resid_vol = (1.0, 0.0) if ticker == "VNINDEX" else (1.05, 0.04 / np.sqrt(TRADING_DAYS))
    else:
        rng_b = np.random.default_rng(_seed_of(ticker))
        beta = float(0.7 + 0.8 * rng_b.random())            # β ∈ [0.7, 1.5]
        # Tách phương sai: σ² tổng = β²σ²_m + σ²_riêng
        total_var = (_VOL_STOCK**2) / TRADING_DAYS
        resid_vol = float(np.sqrt(max(total_var - (beta * _MARKET_VOL) ** 2, 1e-8)))

    rng = np.random.default_rng(_seed_of(ticker) + 1)
    r = beta * rm + resid_vol * rng.standard_normal(n)

    close = s0 * np.exp(np.cumsum(r - r.mean()))            # neo mức giá quanh s0

    # Dựng OHLC quanh close sao cho luôn thỏa low ≤ open, close ≤ high
    intraday = np.abs(rng.standard_normal((n, 3))) * resid_vol * close[:, None]
    open_ = np.concatenate([[close[0]], close[:-1]]) * (1 + rng.standard_normal(n) * resid_vol * 0.3)
    high = np.maximum(close, open_) + intraday[:, 0]
    low = np.minimum(close, open_) - intraday[:, 1]
    low = np.maximum(low, 0.01)

    base_vol = 1_500_000 if idx else 800_000
    volume = np.round(base_vol * np.exp(rng.standard_normal(n) * 0.45)).astype(float)

    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=pd.DatetimeIndex(dates, name="date"),
    )
