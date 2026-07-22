# tests/test_indicators.py
import pandas as pd
import numpy as np
import sys
import os
import pytest

# Cấu hình đường dẫn để pytest nhận diện được thư mục core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.indicators import calculate_sma

def test_calculate_sma_correctness():
    """Kiểm tra xem hàm SMA có tính toán đúng trung bình cộng hay không."""
    
    # 1. Chuẩn bị Mock Data cực kỳ đơn giản để dễ nhẩm nghiệm
    data = {'Close': [10.0, 20.0, 30.0, 40.0, 50.0]}
    df = pd.DataFrame(data)
    
    # 2. Thực thi hàm tính SMA với chu kỳ 3 ngày (window=3)
    result = calculate_sma(df, window=3, column='Close')
    
    # 3. Đối chiếu kết quả (Assertions)
    # Hai ngày đầu tiên chưa đủ chu kỳ 3 ngày, kết quả bắt buộc phải là NaN
    assert np.isnan(result.iloc[0]), "Lỗi: Ngày 1 phải là NaN"
    assert np.isnan(result.iloc[1]), "Lỗi: Ngày 2 phải là NaN"
    
    # Ngày 3: Trung bình của (10 + 20 + 30) / 3 = 20.0
    assert result.iloc[2] == 20.0, "Lỗi: Sai kết quả toán học ngày 3"
    
    # Ngày 5: Trung bình của (30 + 40 + 50) / 3 = 40.0
    assert result.iloc[4] == 40.0, "Lỗi: Sai kết quả toán học ngày 5"

def test_calculate_sma_missing_column():
    """Kiểm tra cơ chế báo lỗi nếu DataFrame đầu vào không có cột được chỉ định."""
    df = pd.DataFrame({'Open': [10, 20, 30]})
    
    # Dùng KeyError vì df không có cột 'Close' mặc định
    with pytest.raises(KeyError):
        calculate_sma(df)
