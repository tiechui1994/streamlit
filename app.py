import streamlit as st
import pathlib
import os
import time
import subprocess

st.header("欢迎来到streamlit项目")

if st.button("打开文件"):
    home = pathlib.Path.home()
    for item in os.listdir(home):
        if pathlib.Path(item).is_file(): st.header(f"文件: {item}")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "一起来 happy"}]

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            st.code(message["content"], language='Go')
        else:
            st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("请输入内容:"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        try:
            result = subprocess.run(prompt, capture_output=True, shell=True, text=True, check=True)
            if result.stdout:
                assistant_response = result.stdout.strip()
            elif result.stderr:
                assistant_response = result.stderr.strip()
        except subprocess.CalledProcessError as e:
            assistant_response = f"错误: {e}"
        except Exception as e:
            assistant_response = f"{e}"
        # Simulate stream of response with milliseconds delay
        for chunk in assistant_response.split('\n'):
            full_response += chunk + "\n"
            time.sleep(0.05)
            # Add a blinking cursor to simulate typing
            message_placeholder.code(full_response + "▌", language='Go')
        message_placeholder.code(full_response, language='Go')
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})