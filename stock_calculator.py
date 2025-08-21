import streamlit as st
import pandas as pd
import math
from decimal import Decimal, getcontext

getcontext().prec = 12  # 避免浮點誤差

st.title("價格區間模擬交易計算")

# --- 輸入參數 ---
trade_type = st.selectbox("交易類型", ["當沖", "非當沖"])
trade_direction = st.selectbox("交易方向", ["做多", "做空"])
buy_price = st.number_input("買入價格 / 賣出價格", min_value=0.01, value=100.0, format="%.2f")
shares = st.number_input("股數", min_value=1, value=1000)
fee_discount = st.number_input("手續費折數（預設2.8折）", min_value=0.1, max_value=10.0, value=2.8, format="%.2f")

# --- 依規則回傳 tick ---
def get_tick(dprice: Decimal) -> Decimal:
    if dprice < Decimal('10'):
        return Decimal('0.01')
    elif dprice < Decimal('50'):
        return Decimal('0.05')
    elif dprice < Decimal('100'):
        return Decimal('0.1')
    elif dprice < Decimal('500'):
        return Decimal('0.5')
    elif dprice < Decimal('1000'):
        return Decimal('1')
    else:
        return Decimal('5')

# 取得「下一個向上/向下」價格（重點：邊界用下一步的區間判斷）
def next_up(dprice: Decimal) -> Decimal:
    step = get_tick(dprice)  # 向上時，使用當前價位的 tick（例如 9.99 -> +0.01 到 10.00；10.00 之後用 0.05）
    return dprice + step

def next_down(dprice: Decimal) -> Decimal:
    # 向下時，若在邊界（例如 10.00），應使用「下一步會落入的區間」的 tick（<10 -> 0.01）
    tiny = Decimal('0.0000001')
    step = get_tick(dprice - tiny)
    return dprice - step

# 顯示目前買入價對應的跳動單位（僅顯示資訊）
current_tick = get_tick(Decimal(str(buy_price)))
st.write(f"依股價設定跳動單位（以當前價顯示）：{float(current_tick)} 元")

# --- 初始化 / 重置價格列表：動態跨區間產生上下各 5 筆 ---
def build_initial_prices(buy: float):
    d = Decimal(str(buy))
    ups, downs = [], []
    t = d
    for _ in range(5):
        t = next_up(t)
        ups.append(float(t))
    t = d
    for _ in range(5):
        t = next_down(t)
        downs.append(float(t))
    return downs[:]()
