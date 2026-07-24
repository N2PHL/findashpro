# core/llm_client.py
import google.generativeai as genai
import streamlit as st

def get_ai_response(messages: list) -> str:
    """Gửi lịch sử hội thoại tới Gemini và nhận câu trả lời."""
    
    # 1. Khởi tạo kết nối bằng Key trong két sắt
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    # 2. Cấu hình mô hình và "Nhân cách" định lượng
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash", # Bản Flash siêu tốc, phù hợp cho Chatbot
        system_instruction=(
            "Bạn là một chuyên gia phân tích định lượng (Quant Analyst) và tư vấn tài chính. "
            "Bạn am hiểu sâu sắc về kinh tế học đầu tư, các mô hình định giá, và quản trị rủi ro. "
            "Câu trả lời của bạn phải ngắn gọn, sắc bén, dựa trên dữ liệu và loại bỏ cảm tính."
        )
    )
    
    # 3. Chuyển đổi lịch sử chat từ chuẩn Streamlit sang chuẩn Gemini
    # Gemini dùng 'user' và 'model' thay vì 'user' và 'assistant'
    gemini_history = []
    
    # Lấy toàn bộ tin nhắn ngoại trừ câu hỏi cuối cùng để làm bối cảnh
    for msg in messages[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [msg["content"]]})
        
    try:
        # Khởi tạo phiên chat với bối cảnh cũ
        chat = model.start_chat(history=gemini_history)
        
        # Gửi câu hỏi mới nhất (phần tử cuối cùng trong list messages)
        response = chat.send_message(messages[-1]["content"])
        return response.text
        
    except Exception as e:
        return f"⚠️ Lỗi kết nối API Gemini: {str(e)}"
        