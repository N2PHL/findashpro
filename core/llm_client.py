# core/llm_client.py
import streamlit as st
from groq import Groq

def get_ai_response(messages: list) -> str:
    """Gửi lịch sử hội thoại tới Groq (chạy mô hình Llama 3) và nhận câu trả lời siêu tốc."""
    
    try:
        # 1. Khởi tạo Client với API Key từ bảo mật Streamlit
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        
        # 2. Đóng gói "Nhân cách" (System Instruction)
        # Khác với Gemini, Groq nhận System Prompt trực tiếp như một tin nhắn đầu tiên
        groq_messages = [
            {
                "role": "system",
                "content": (
                    "Bạn là một chuyên gia phân tích định lượng (Quant Analyst) và tư vấn tài chính. "
                    "Bạn am hiểu sâu sắc về kinh tế học đầu tư, các mô hình định giá, và quản trị rủi ro. "
                    "Câu trả lời của bạn phải ngắn gọn, sắc bén, dựa trên dữ liệu và loại bỏ cảm tính."
                )
            }
        ]
        
        # 3. Kế thừa trực tiếp lịch sử chat từ Streamlit (không cần biến đổi role)
        for msg in messages:
            groq_messages.append({
                "role": msg["role"], 
                "content": msg["content"]
            })
            
                 # 4. Gửi truy vấn tới máy chủ Groq
        # ĐÃ SỬA: Sử dụng model mã nguồn mở thế hệ mới nhất theo tài liệu Deprecation của Groq
        chat_completion = client.chat.completions.create(
            messages=groq_messages,
            model="openai/gpt-oss-120b", 
            temperature=0.2, 
            max_tokens=2048
        )
        
        # 5. Trích xuất và trả về kết quả
        return chat_completion.choices[0].message.content
        
    except Exception as e:
        return f"⚠️ Lỗi kết nối luồng dữ liệu Groq API: {str(e)}"
    