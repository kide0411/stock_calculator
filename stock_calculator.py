import streamlit as st
import pandas as pd
import math
from decimal import Decimal, getcontext

# --- 避免浮點誤差 ---
getcontext().prec = 12

st.title("價格區間模擬交易計算")

# --- 輸入參數 ---
trade_type = st.selectbox("交易類型", ["當沖", "非當沖"])
trade_direction = st.selectbox("交易方向", ["做多", "做空"])
buy_price = st.number_input("買入價格 / 賣出價格", min_value=0.01, value=100.0, format="%.2f")
shares = st.number_input("股數", min_value=1, value=1000)
fee_discount = st.number_input("手續費折數（預設2.8折）", min_value=0.1, max_value=10.0, value=2.8, format="%.2f")

# --- 股價跳動單位規則 ---
def get_tick(price: Decimal) -> Decimal:
    if price < Decimal('10'):
        return Decimal('0.01')
    elif price < Decimal('50'):
        return Decimal('0.05')
    elif price < Decimal('100'):
        return Decimal('0.1')
    elif price < Decimal('500'):
        return Decimal('0.5')
    elif price < Decimal('1000'):
        return Decimal('1')
    else:
        return Decimal('5')

def next_up(price: Decimal) -> Decimal:
    step = get_tick(price)
    return price + step

def next_down(price: Decimal) -> Decimal:
    tiny = Decimal('0.0000001')
    step = get_tick(price - tiny)
    return price - step

# --- 初始價區間 ---
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
    return downs[::-1] + [float(buy)] + ups

# --- 初始化 session state ---
if "base_prices" not in st.session_state or st.session_state.get("buy_price") != buy_price:
    st.session_state.base_prices = build_initial_prices(buy_price)
    st.session_state.buy_price = buy_price

# --- 成本/獲利計算 ---
def calculate_profit(b_price, s_price, shares, fee_discount, trade_type, trade_direction):
    fee_rate = 0.001425
    tax_rate = 0.0015 if trade_type == "當沖" else 0.003

    entry_notional = b_price * shares
    exit_notional  = s_price * shares

    fee = math.floor(max((entry_notional + exit_notional) * fee_rate * (fee_discount / 10), 20))

    if trade_direction == "做多":
        tax_base = exit_notional
        tax = math.floor(tax_base * tax_rate)
        profit = exit_notional - entry_notional - fee - tax
    else:  # 做空
        tax_base = entry_notional
        tax = math.floor(tax_base * tax_rate)
        profit = entry_notional - exit_notional - fee - tax

    profit = math.floor(profit)
    roi = round((profit / entry_notional) * 100, 2)  # 保留兩位小數

    return fee, tax, profit, roi

# --- 生成表格 ---
def generate_table(prices):
    prices_sorted = sorted(set(prices))
    rows = []
    for s_price in prices_sorted:
        fee, tax, profit, roi = calculate_profit(buy_price, s_price, shares, fee_discount, trade_type, trade_direction)
        rows.append([buy_price, s_price, tax, fee, profit, f"{roi:.2f}%"])
    return pd.DataFrame(rows, columns=["買入價格","賣出價格","證交稅","總手續費","獲利","報酬率"])

# --- 更多價格 ---
def add_upper_prices():
    last_max = max(st.session_state.base_prices + [buy_price])
    d = Decimal(str(last_max))
    for _ in range(5):
        d = next_up(d)
        st.session_state.base_prices.append(float(d))

def add_lower_prices():
    last_min = min(st.session_state.base_prices + [buy_price])
    d = Decimal(str(last_min))
    new_list = []
    for _ in range(5):
        d = next_down(d)
        new_list.append(float(d))
    st.session_state.base_prices = new_list + st.session_state.base_prices

# --- 顯示表格與按鈕 ---
st.subheader("價格區間模擬結果（依賣出價格排序）")

# 左上角：更多下方價格
c1, _, _ = st.columns([1,4,1])
with c1:
    if st.button("顯示更多價格", key="more_down"):
        add_lower_prices()

# 表格
df = generate_table(st.session_state.base_prices)
st.dataframe(df)

# 右下角：更多上方價格
_, _, c3 = st.columns([4,1,1])
with c3:
    if st.button("顯示更多價格", key="more_up"):
        add_upper_prices()
