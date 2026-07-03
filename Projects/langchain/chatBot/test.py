import streamlit as st

# 设置标题
st.title('平方计算器')

# 创建一个滑块
number = st.slider("Select a number:", min_value=0, max_value=100)

# 显示选中数字的平方
st.write(f"Square of {number} is {number ** 2}")
