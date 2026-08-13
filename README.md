# FinDash Pro v2 — Bảng phân tích tài chính thị trường chứng khoán Việt Nam

Ứng dụng Streamlit tám trang: dữ liệu giá, thống kê mô tả, báo cáo tài chính,
mô hình định giá tài sản (CAPM, APT), mô phỏng Monte Carlo, kiểm thử chiến lược
và tối ưu hóa danh mục.

```bash
pip install -r requirements.txt
python kiem_tra.py          # tự kiểm tra 22 mục, không cần mạng
streamlit run app.py
```

---

## Đối chiếu với đề bài

| # | Yêu cầu | Nơi thực hiện |
|---|---------|---------------|
| [1] | Tổng quan, chọn từ danh sách cổ phiếu | `pages/1_Summary` · danh sách ở `utils/config.UNIVERSE` (35 mã / 6 nhóm ngành) |
| [2] | Biểu đồ, lấy mẫu ngày/tuần/tháng, Line/Candle | `pages/2_Advanced_Chart` · `dnse_client.resample_ohlcv` |
| [3] | Thống kê, tài chính, phân tích giá | `pages/3_Financials` · `quantitative.describe_returns` |
| [4] | Danh mục: CAPM, APT | `pages/4_Risk_Analytics` (một mã), `pages/7_Portfolio` (danh mục) · `core/portfolio.py` |
| [5] | Mô phỏng Monte Carlo | `pages/4_Risk_Analytics` · `quantitative.run_monte_carlo` |

Ba trang mở rộng ngoài đề: Alpha Backtest, Risk Optimization, AI Assistant.

---

## Kiến trúc

```
app.py                  Trang chủ, điều hướng
pages/                  8 trang giao diện — chỉ gọi hàm, không chứa logic tài chính
core/                   Mô hình định lượng
  quantitative.py         Monte Carlo (GBM + Bootstrap), thống kê mô tả
  portfolio.py            CAPM, APT, dựng nhân tố, chuỗi NAV danh mục
  portfolio_opt.py        Mean-variance, đường biên hiệu quả, Ledoit–Wolf, VaR/CVaR, Kupiec
  alpha_engine.py         Tín hiệu và kiểm thử chiến lược theo ràng buộc TTCK Việt Nam
  indicators.py           RSI, Bollinger
  llm_client.py           Trợ lý AI (Groq)
data/                   Truy cập dữ liệu
  dnse_client.py          Giá OHLCV (entrade), lấy mẫu lại, điều chỉnh sự kiện quyền
  yfinance_client.py      Báo cáo tài chính, hồ sơ doanh nghiệp
  mock_data.py            Dữ liệu dự phòng khi API không phản hồi
ui/                     Thành phần và biểu đồ dùng chung
utils/config.py         NGUỒN KHAI BÁO DUY NHẤT cho mọi tham số tài chính
kiem_tra.py             Kiểm tra toàn hệ thống trước khi commit
```

---

## Các quyết định phương pháp cần biết khi bảo vệ

**Lãi suất phi rủi ro khai báo một lần** tại `utils/config.RISK_FREE_RATE = 4.5%/năm`.
Mọi module đọc từ đó. Hai giá trị khác nhau ở hai trang sẽ khiến Sharpe ratio và
lợi suất yêu cầu theo CAPM không so sánh được với nhau.

**Quy ước lợi suất là log return** trên toàn ứng dụng, không trộn với simple return.

**Monte Carlo dùng GBM có hiệu chỉnh Itô:**
`S_t = S₀·exp(Σ[(μ − ½σ²)Δt + σ√Δt·Z])`.
Bỏ số hạng −½σ² làm kỳ vọng bị thổi lên đúng hệ số `exp(σ²T/2)`. Drift là tham số
chọn được (lịch sử / trung tính rủi ro / martingale) vì drift lịch sử có sai số
chuẩn lớn hơn chính giá trị ước lượng — xem `quantitative.estimate_drift`.
Có sẵn phương án Bootstrap để đối chiếu, do GBM giả định phân phối chuẩn trong khi
Jarque–Bera trên dữ liệu thật gần như luôn bác bỏ giả định đó.

**VaR là một khoản lỗ, không phải một mức giá:** `VaR₉₅ = S₀ − Q₅(S_T)`.
Mẫu dưới 100 quan sát bị chặn bằng lỗi tường minh thay vì trả NaN im lặng.
Có kiểm định Kupiec vì VaR ở đây là in-sample.

**Đường biên hiệu quả giải bằng tối ưu**, tại mỗi mức lợi suất mục tiêu giải
`min wᵀΣw`. Đám mây danh mục ngẫu nhiên chỉ dùng làm nền minh họa và được gọi
đúng tên như vậy.

**Hiệp phương sai mặc định co theo Ledoit–Wolf** về mục tiêu tương quan hằng số.
Bộ tối ưu mean-variance khuếch đại sai số ước lượng của ma trận mẫu; hệ số co δ
được ước lượng từ dữ liệu và hiển thị trên giao diện.

**Backtest theo ràng buộc thị trường Việt Nam:** không bán khống, thanh toán T+2,
tín hiệu tính hết phiên T khớp lệnh phiên T+1, có tính phí 0,15%/lượt.
Sharpe có trừ lãi suất phi rủi ro; đại lượng không trừ rf được gọi đúng tên là
Information Ratio.

**Xử lý dữ liệu:** khối lượng khuyết điền 0 chứ không ffill (ffill tạo thanh khoản
không tồn tại). Báo cáo tài chính khuyết giữ nguyên NaN chứ không điền 0 (điền 0
biến "API không trả dữ liệu" thành "doanh thu bằng không").

---

## Giới hạn đã biết

**Điều chỉnh sự kiện quyền là suy luận, không phải dữ liệu chính thức.**
`dnse_client.detect_corporate_actions` nhận diện chia tách qua bước nhảy vượt trần
biên độ ±7% của HOSE. Cách này không phân biệt được cổ tức tiền mặt lớn với chia
tách và bỏ sót các đợt chia nhỏ dưới ngưỡng. Nguồn đúng là bản tin quyền của sở
giao dịch.

**Báo cáo tài chính lấy từ Yahoo Finance** với hậu tố `.VN`. Yahoo phủ mã HOSE
không đầy đủ; nhiều trường trả về rỗng. Ứng dụng hiển thị ô trống thay vì điền 0.
Nguồn tốt hơn là dữ liệu nội địa (vnstock, TCBS).

**Endpoint `services.entrade.com.vn` là API nội bộ**, không có tài liệu công khai
và không có cam kết ổn định. Khi API không phản hồi, ứng dụng chuyển sang
`data/mock_data.py` và gắn nhãn "dữ liệu mô phỏng" ngay cạnh số liệu.

**VaR từ GBM ước lượng thấp rủi ro một cách có hệ thống** do thị trường có đuôi
dày và volatility clustering. Dùng phương án Bootstrap để đối chiếu.

---

## Cấu hình khóa API (chỉ cần cho trang trợ lý AI)

Khóa **không** được đặt trong mã nguồn. Bảy trang còn lại chạy bình thường khi
chưa cấu hình khóa.

Chạy tại máy — tạo `.streamlit/secrets.toml` (đã nằm trong `.gitignore`):

```toml
GROQ_API_KEY = "gsk_..."
```

Trên Streamlit Cloud — **Manage app → Settings → Secrets**, dán đúng dòng trên.
Lấy khóa tại `console.groq.com/keys`.
