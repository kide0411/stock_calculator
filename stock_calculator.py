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
    return downs[::-1] + ups  # 下方由小到大 + 上方由小到大（最終我們仍會排序保險）

if "base_prices" not in st.session_state or st.session_state.get("buy_price") != buy_price:
    st.session_state.base_prices = build_initial_prices(buy_price)
    st.session_state.buy_price = buy_price

# --- 計算（無條件捨去） ---
def calculate_profit(b_price, s_price, shares, fee_discount, trade_type, trade_direction):
    fee_rate = 0.001425
    tax_rate = 0.0015 if trade_type == "當沖" else 0.003
    buy_amount = b_price * shares
    sell_amount = s_price * shares
    fee = math.floor(max((buy_amount + sell_amount) * fee_rate * (fee_discount / 10), 20))
    tax = math.floor(sell_amount * tax_rate) if trade_direction == "做多" else math.floor(buy_amount * tax_rate)
    profit = math.floor(sell_amount - buy_amount - fee - tax)
    roi = math.floor((profit / buy_amount) * 100)
    return fee, tax, profit, roi

# --- 生成表格（賣出價排序、報酬率加 %） ---
def generate_table(prices):
    prices_sorted = sorted(prices)
    rows = []
    for s_price in prices_sorted:
        fee, tax, profit, roi = calculate_profit(buy_price, s_price, shares, fee_discount, trade_type, trade_direction)
        rows.append([buy_price, s_price, tax, fee, profit, f"{roi}%"])
    return pd.DataFrame(rows, columns=["買入價格","賣出價格","證交稅","總手續費","獲利","報酬率"])

# --- 延伸按鈕（逐步跨區間生成，確保邊界正確） ---
def add_upper_prices():
    if not st.session_state.base_prices:
        st.session_state.base_prices = build_initial_prices(buy_price)
    last_max = max(st.session_state.base_prices + [buy_price])
    d = Decimal(str(last_max))
    for _ in range(5):
        d = next_up(d)
        st.session_state.base_prices.append(float(d))

def add_lower_prices():
    if not st.session_state.base_prices:
        st.session_state.base_prices = build_initial_prices(buy_price)
    last_min = min(st.session_state.base_prices + [buy_price])
    d = Decimal(str(last_min))
    new_list = []
    for _ in range(5):
        d = next_down(d)
        new_list.append(float(d))
    st.session_state.base_prices = new_list + st.session_state.base_prices

# --- 按鈕 ---
c1, c2 = st.columns(2)
with c1:
    if st.button("更多上方價格"):
        add_upper_prices()
with c2:
    if st.button("更多下方價格"):
        add_lower_prices()

# --- 顯示 ---
df = generate_table(st.session_state.base_prices)
st.subheader("價格區間模擬結果（依賣出價格排序）")
st.dataframe(df)
