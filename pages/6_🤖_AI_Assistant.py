# pages/6_🤖_AI_Assistant.py
import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.llm_client import get_ai_response

def render_chat_page():
    st.title("🤖 Trợ Lý Phân Tích Định Lượng (Powered by Gemini)")
    st.markdown("Trao đổi trực tiếp với AI về các chiến lược giao dịch, kinh tế vĩ mô và phân tích rủi ro.")
    
    # Khởi tạo bộ nhớ tạm để lưu lịch sử chat
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Chào bạn, tôi có thể giúp gì cho việc phân tích danh mục hoặc thẩm định dự án hôm nay?"}
        ]

    # Render lại toàn bộ lịch sử tin nhắn ra màn hình
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Khung nhập liệu của người dùng
    if prompt := st.chat_input("Nhập câu hỏi về thị trường hoặc mô hình kinh tế lượng..."):
        
        # 1. Hiển thị tin nhắn người dùng
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # 2. Lưu vào bộ nhớ trạng thái
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # 3. Gửi cho Gemini và chờ phản hồi
        with st.chat_message("assistant"):
            with st.spinner("Đang tính toán ma trận ngôn ngữ..."):
                # Gom toàn bộ lịch sử chat gửi sang backend
                api_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                
                # Gọi hàm từ core/llm_client.py
                response = get_ai_response(api_messages)
                
                st.markdown(response)
                
        # 4. Lưu phản hồi của AI vào hệ thống
        st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    render_chat_page()
    