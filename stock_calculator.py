import streamlit as st
import pandas as pd
import math  # 用來無條件捨去

st.title("價格區間模擬交易計算")

# --- 輸入參數 ---
trade_type = st.selectbox("交易類型", ["當沖", "非當沖"])
trade_direction = st.selectbox("交易方向", ["做多", "做空"])
buy_price = st.number_input("買入價格 / 賣出價格", min_value=0.01, value=100.0, format="%.2f")
shares = st.number_input("股數", min_value=1, value=1000)
fee_discount = st.number_input("手續費折數（預設2.8折）", min_value=0.1, max_value=10.0, value=2.8, format="%.2f")

# --- 判斷跳動單位 ---
def get_price_step(price):
    if price < 10:
        return 0.01
    elif price < 50:
        return 0.05
    elif price < 100:
        return 0.1
    elif price < 500:
        return 0.5
    elif price < 1000:
        return 1
    else:
        return 5

def round_price(price):
    step = get_price_step(price)
    return round(price / step) * step

price_step = get_price_step(buy_price)
st.write(f"依股價設定跳動單位: {price_step} 元")

# --- 初始化 session_state ---
if "base_prices" not in st.session_state or st.session_state.get("buy_price", 0) != buy_price:
    st.session_state.base_prices = [round_price(buy_price + i * price_step) for i in range(1, 6)] + \
                                   [round_price(buy_price - i * price_step) for i in range(5, 0, -1)]
    st.session_state.buy_price = buy_price

if "price_step" not in st.session_state:
    st.session_state.price_step = price_step

# --- 計算利潤函數 (無條件捨去) ---
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

# --- 生成表格函數 (報酬率加 % 單位) ---
def generate_table(base_prices):
    data = []
    for s_price in base_prices:
        s_price = round_price(s_price)
        fee, tax, profit, roi = calculate_profit(buy_price, s_price, shares, fee_discount, trade_type, trade_direction)
        data.append([buy_price, s_price, tax, fee, profit, f"{roi}%"])
    return pd.DataFrame(data, columns=["買入價格","賣出價格","證交稅","總手續費","獲利","報酬率"])

# --- 延伸價格函數 (依跳動單位 + 四捨五入) ---
def add_upper_prices():
    last_max = max(st.session_state.base_prices, default=buy_price)
    step = get_price_step(last_max)
    st.session_state.base_prices.extend([round_price(last_max + i * step) for i in range(1,6)])

def add_lower_prices():
    last_min = min(st.session_state.base_prices, default=buy_price)
    step = get_price_step(last_min)
    st.session_state.base_prices = [round_price(last_min - i * step) for i in range(5,0,-1)] + st.session_state.base_prices

# --- 按鈕操作 ---
col1, col2 = st.columns(2)
with col1:
    if st.button("更多上方價格"):
        add_upper_prices()
with col2:
    if st.button("更多下方價格"):
        add_lower_prices()

# --- 顯示表格 ---
df = generate_table(st.session_state.base_prices)
st.subheader("價格區間模擬結果")
st.dataframe(df)
