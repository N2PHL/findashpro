# data/yfinance_client.py
"""
Lớp truy cập dữ liệu cơ bản (Yahoo Finance).

Ba quy ước của lớp dữ liệu cơ bản:
  1. Giá trị khuyết được giữ nguyên trạng thái khuyết, không điền 0. Trong báo cáo
     tài chính, "nguồn không trả dữ liệu" và "khoản mục bằng 0" là hai tình trạng
     khác hẳn nhau: điền 0 vào một kỳ khuyết doanh thu sẽ làm mọi tỷ suất suy ra từ
     nó bằng 0 hoặc không xác định, đồng thời kéo lệch mọi thống kê theo chuỗi.
  2. Hậu tố thị trường là tham số, không cố định là ".VN", nên cùng một module dùng
     được cho cả cổ phiếu niêm yết trong nước lẫn nước ngoài.
  3. Kết quả được cache. yf.Ticker().info là lời gọi chậm và dễ bị giới hạn tần suất
     nhất trong toàn bộ ứng dụng, trong khi Streamlit chạy lại script sau mỗi tương
     tác của người dùng.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

from utils.logger import get_logger

log = get_logger("yfinance")

MARKETS = {"Việt Nam (HOSE/HNX)": ".VN", "Quốc tế (US/EU/…)": ""}


def to_symbol(ticker: str, suffix: str = ".VN") -> str:
    """VCB + '.VN' -> 'VCB.VN' ; AAPL + '' -> 'AAPL'."""
    return f"{ticker.strip().upper()}{suffix}"


def clean_yfinance_data(df: pd.DataFrame, is_financial_statement: bool = False) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.replace([np.inf, -np.inf], np.nan)

    if is_financial_statement:
        df = df.dropna(how="all")
        # KHÔNG fillna(0). NaN được giữ nguyên để người đọc THẤY ô trống và biết
        # đó là dữ liệu thiếu. Pandas/Plotly tự bỏ qua NaN khi tính và vẽ.
    return df


@st.cache_data(ttl=900, show_spinner=False)
def fetch_company_profile(ticker: str, suffix: str = ".VN") -> dict:
    """Hồ sơ doanh nghiệp cho trang Summary (yêu cầu [1])."""
    try:
        info = yf.Ticker(to_symbol(ticker, suffix)).info or {}
    except Exception as exc:                       # noqa: BLE001
        log.error("Lỗi profile %s: %s", ticker, exc)
        return {}

    return {
        "Tên công ty": info.get("longName") or info.get("shortName"),
        "Sàn niêm yết": info.get("exchange"),
        "Ngành": info.get("sector"),
        "Lĩnh vực": info.get("industry"),
        "Vốn hóa": info.get("marketCap"),
        "CP lưu hành": info.get("sharesOutstanding"),
        "Tiền tệ": info.get("currency"),
        "Website": info.get("website"),
        "Mô tả": info.get("longBusinessSummary"),
    }


@st.cache_data(ttl=900, show_spinner=False)
def fetch_financial_ratios(ticker: str, suffix: str = ".VN") -> pd.DataFrame:
    """
    Chỉ số định giá. Trả về DataFrame 2 cột (Chỉ số / Giá trị) đã ĐỊNH DẠNG SẴN,
    Các tỷ suất được đưa về dạng phần trăm có nhãn, tránh hiển thị số thập phân thô
    (0.2134) khiến người đọc không phân biệt được đơn vị.
    """
    try:
        info = yf.Ticker(to_symbol(ticker, suffix)).info or {}
    except Exception as exc:                       # noqa: BLE001
        log.error("Lỗi ratios %s: %s", ticker, exc)
        return pd.DataFrame()

    cur = info.get("currency", "")
    raw = {
        "P/E (trailing)": (info.get("trailingPE"), "x"),
        "P/E (forward)": (info.get("forwardPE"), "x"),
        "P/B": (info.get("priceToBook"), "x"),
        "EPS (trailing)": (info.get("trailingEps"), cur),
        "ROE": (info.get("returnOnEquity"), "%"),
        "ROA": (info.get("returnOnAssets"), "%"),
        "Biên LN gộp": (info.get("grossMargins"), "%"),
        "Biên LN ròng": (info.get("profitMargins"), "%"),
        "Nợ / Vốn CSH": (info.get("debtToEquity"), "%"),
        "Tỷ suất cổ tức": (info.get("dividendYield"), "%"),
        "Beta (Yahoo)": (info.get("beta"), "x"),
        f"Vốn hóa ({cur})": (info.get("marketCap"), "tiền"),
    }

    rows = []
    for name, (val, unit) in raw.items():
        if val is None or (isinstance(val, float) and np.isnan(val)):
            shown = "—"                     # ô trống trung thực, KHÔNG phải số 0
        elif unit == "%":
            shown = f"{val:.2%}"
        elif unit == "tiền":
            shown = f"{val/1e9:,.0f} tỷ"
        elif unit == "x":
            shown = f"{val:,.2f}x"
        else:
            shown = f"{val:,.2f} {unit}".strip()
        rows.append({"Chỉ số": name, "Giá trị": shown, "_missing": shown == "—"})

    return pd.DataFrame(rows)


def coverage(df_ratios: pd.DataFrame) -> float:
    """Tỷ lệ trường bị thiếu — dùng để cảnh báo trung thực thay vì hiện bảng NaN im lặng."""
    if df_ratios.empty or "_missing" not in df_ratios.columns:
        return 1.0
    return float(df_ratios["_missing"].mean())


@st.cache_data(ttl=900, show_spinner=False)
def fetch_statement(ticker: str, kind: str = "income",
                    is_yearly: bool = False, suffix: str = ".VN") -> pd.DataFrame:
    """
    Báo cáo tài chính: kết quả kinh doanh, cân đối kế toán và lưu chuyển tiền tệ.
    kind ∈ {"income", "balance", "cashflow"}
    """
    try:
        stock = yf.Ticker(to_symbol(ticker, suffix))
        table = {
            ("income", True): "financials", ("income", False): "quarterly_financials",
            ("balance", True): "balance_sheet", ("balance", False): "quarterly_balance_sheet",
            ("cashflow", True): "cashflow", ("cashflow", False): "quarterly_cashflow",
        }[(kind, is_yearly)]
        raw = getattr(stock, table)
    except Exception as exc:                       # noqa: BLE001
        log.error("Lỗi %s %s: %s", kind, ticker, exc)
        return pd.DataFrame()

    df = clean_yfinance_data(raw, is_financial_statement=True)
    if not df.empty:
        df.columns = [c.strftime("%Y-%m-%d") if hasattr(c, "strftime") else str(c)
                      for c in df.columns]
    return df


# Giữ tên hàm cũ để không phá vỡ mã đã import ở nơi khác
def fetch_income_statement(ticker: str, is_yearly: bool = False,
                           suffix: str = ".VN") -> pd.DataFrame:
    return fetch_statement(ticker, "income", is_yearly, suffix)
