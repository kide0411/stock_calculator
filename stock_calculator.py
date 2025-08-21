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
    step = get_tick(price)   # 向上用當前價格的 tick
    return price + step

def next_down(price: Decimal) -> Decimal:
    tiny = Decimal('0.0000001')
    step = get_tick(price - tiny)  # 向下用「下一步會落入區間」的 tick
    return price - step

# --- 初始價區間：上下各5筆 + 中間放買入價 ---
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

# --- 成本/獲利計算（無條件捨去；做多/做空分流） ---
def calculate_profit(b_price, s_price, shares, fee_discount, trade_type, trade_direction):
    fee_rate = 0.001425
    tax_rate = 0.0015 if trade_type == "當沖" else 0.003

    # 進出場名目金額（皆用正數）
    entry_notional = b_price * shares     # 做多：買入金額；做空：進場賣出金額（用輸入價做進場）
    exit_notional  = s_price * shares     # 做多：賣出金額；做空：出場買回金額

    # 手續費（雙邊），最低20元，無條件捨去
    fee = math.floor(max((entry_notional + exit_notional) * fee_rate * (fee_discount / 10), 20))

    # 證交稅：只課徵在賣出的一邊
    if trade_direction == "做多":
        tax_base = exit_notional          # 做多的賣出在出場
        profit = exit_notional - entry_notional - fee - math.floor(tax_base * tax_rate)
    else:  # 做空
        tax_base = entry_notional         # 做空的賣出在進場
        profit = entry_notional - exit_notional - fee - math.floor(tax_base * tax_rate)

    profit = math.floor(profit)

    # 報酬率以「進場名目金額」為分母
    roi = math.floor((profit / entry_notional) * 100)
    tax = math.floor(tax_base * tax_rate)
    return fee, tax, profit, roi

# --- 生成表格（含買入價，賣出價排序，報酬率加%） ---
def generate_table(prices):
    prices_sorted = sorted(set(prices))
    rows = []
    for s_price in prices_sorted:
        fee, tax, profit, roi = calculate_profit(buy_price, s_price, shares, fee_discount, trade_type, trade_direction)
        rows.append([buy_price, s_price, tax, fee, profit, f"{roi}%"])
    return pd.DataFrame(rows, columns=["買入價格","賣出價格","證交稅","總手續費","獲利","報酬率"])

# --- 更多上下價格（逐步跨區間，確保邊界正確） ---
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

# --- 按鈕 ---
c1, c2 = st.columns(2)
with c1:
    if st.button("更多上方價格"):
        add_upper_prices()
with c2:
    if st.button("更多下方價格"):
        add_lower_prices()

# --- 顯示結果 ---
df = generate_table(st.session_state.base_prices)
st.subheader("價格區間模擬結果（依賣出價格排序）")
st.dataframe(df)
