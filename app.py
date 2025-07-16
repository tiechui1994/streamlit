import streamlit as st
import pathlib
import os

st.header("欢迎来到streamlit项目")

if st.button("打开文件"):
    home = pathlib.Path.home()
    for item in os.listdir(home):
        pass
