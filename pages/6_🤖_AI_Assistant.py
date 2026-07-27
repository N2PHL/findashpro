# pages/6_🤖_AI_Assistant.py
import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.llm_client import get_ai_response 

def render_chat_page():
    # --- 1. QUẢN LÝ TRẠNG THÁI (SESSION STATE) ---
    if 'ticker' not in st.session_state:
        st.session_state['ticker'] = 'VCB'
        
    # Khởi tạo bộ nhớ tạm để lưu lịch sử chat
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": f"Chào bạn, hệ thống đang định vị mã **{st.session_state['ticker']}**. Tôi có thể giúp gì cho việc phân tích danh mục hoặc kiểm thử thuật toán hôm nay?"}
        ]

    # --- 2. SIDEBAR ĐỒNG BỘ ---
    st.sidebar.markdown("### ⚙️ Bảng Điều Khiển")
    st.sidebar.divider()
    
    input_ticker = st.sidebar.text_input(
        "Nhập mã cổ phiếu (Ticker):", 
        value=st.session_state['ticker'],
        key="ai_assistant_ticker_input"
    ).upper()
    
    # Cập nhật State và thông báo cho AI biết ngữ cảnh đã thay đổi
    if input_ticker != st.session_state['ticker']:
        st.session_state['ticker'] = input_ticker
        
        # QUAN TRỌNG: Dán nhãn 'is_system' để phân biệt tin nhắn UI và tin nhắn API
        st.session_state.messages.append({
            "role": "assistant", 
            "content": f"🔄 Hệ thống đã chuyển mục tiêu sang phân tích mã **{input_ticker}**. Bạn cần truy vấn thông tin gì?",
            "is_system": True 
        })
        st.rerun()

    current_ticker = st.session_state['ticker']

    # --- 3. GIAO DIỆN CHÍNH (COMMAND CENTER) ---
    st.markdown("""
        <style>
        .terminal-header {
            font-family: 'Courier New', Courier, monospace;
            color: #ff9900;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f'<h1 class="terminal-header">🤖 Trợ Lý Quant AI: {current_ticker}</h1>', unsafe_allow_html=True)
    st.caption("Trao đổi trực tiếp với LLM về các chiến lược giao dịch, kinh tế vĩ mô và viết code thuật toán định lượng.")
    st.divider()

    # --- 4. RENDER LỊCH SỬ CHAT ---
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- 5. XỬ LÝ LOGIC CHAT (PROMPT) ---
    if prompt := st.chat_input(f"Nhập câu hỏi về {current_ticker} hoặc mô hình kinh tế lượng..."):
        
        # Hiển thị tin nhắn người dùng
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # Lưu vào bộ nhớ trạng thái
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Gửi cho Gemini và chờ phản hồi
        with st.chat_message("assistant"):
            with st.spinner("Đang tính toán ma trận ngôn ngữ..."):
                
                # QUAN TRỌNG: Lọc mảng dữ liệu trước khi gửi sang file llm_client.py
                # Chỉ lấy những tin nhắn thực sự của user và AI, bỏ qua các thông báo đổi mã (is_system)
                # Điều này giúp bảo vệ tính toàn vẹn xen kẽ (user -> model).
                api_messages = [
                    {"role": m["role"], "content": m["content"]} 
                    for m in st.session_state.messages 
                    if not m.get("is_system", False)
                ]
                
                # Gọi hàm từ core/llm_client.py
                response = get_ai_response(api_messages)
                
                st.markdown(response)
                
        # Lưu phản hồi của AI vào hệ thống
        st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    render_chat_page()
