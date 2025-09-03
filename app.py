from flask import Flask, request
import requests, os, random

app = Flask(__name__)

# ====== CONFIG ======
TOKEN = os.getenv("BOT_TOKEN")
CG_API_KEY = os.getenv("CG_API_KEY")
TAAPI_KEY = os.getenv("TAAPI_KEY")
API_URL = f"https://api.telegram.org/bot{TOKEN}/"


# ====== FUNCTION: Send Message ======
def send_message(chat_id, text, buttons=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    requests.post(API_URL + "sendMessage", json=payload)


# ====== FUNCTION: Get Crypto Price ======
def get_price(symbol):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd"
    headers = {"x-cg-demo-api-key": CG_API_KEY}
    r = requests.get(url, headers=headers).json()
    return r.get(symbol, {}).get("usd", 0)


# ====== FUNCTION: Get Top Coins ======
def get_top_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 50,
        "page": 1,
        "sparkline": False,
        "price_change_percentage": "24h"
    }
    headers = {"x-cg-demo-api-key": CG_API_KEY}
    data = requests.get(url, params=params, headers=headers).json()

    if not data:
        return "⚠️ Error fetching data."

    # Top gainers
    sorted_gainers = sorted(data, key=lambda x: x["price_change_percentage_24h"] or 0, reverse=True)
    gainers = sorted_gainers[:5]

    # Top losers
    sorted_losers = sorted(data, key=lambda x: x["price_change_percentage_24h"] or 0)
    losers = sorted_losers[:5]

    msg = "📊 <b>Top 5 Gainers</b>\n"
    for c in gainers:
        msg += f"✅ {c['name']} ({c['symbol'].upper()}) +{round(c['price_change_percentage_24h'], 2)}%\n"

    msg += "\n📉 <b>Top 5 Losers</b>\n"
    for c in losers:
        msg += f"❌ {c['name']} ({c['symbol'].upper()}) {round(c['price_change_percentage_24h'], 2)}%\n"

    return msg


# ====== FUNCTION: TAAPI Signal ======
def get_signal(symbol):
    intervals = ["1h", "4h", "1d"]
    msg = f"📊 <b>Signal for {symbol}</b>\n"

    for intv in intervals:
        # RSI
        url_rsi = f"https://api.taapi.io/rsi?secret={TAAPI_KEY}&exchange=binance&symbol={symbol}/USDT&interval={intv}"
        rsi = requests.get(url_rsi).json()
        rsi_val = rsi.get("value", 0)

        # MACD
        url_macd = f"https://api.taapi.io/macd?secret={TAAPI_KEY}&exchange=binance&symbol={symbol}/USDT&interval={intv}"
        macd = requests.get(url_macd).json()
        macd_hist = macd.get("valueMACDHist", 0)

        if rsi_val < 30 and macd_hist > 0:
            signal = "🟢 Strong Buy"
        elif rsi_val > 70 and macd_hist < 0:
            signal = "🔴 Strong Sell"
        else:
            signal = "⚪ Neutral"

        msg += f"⏱ {intv} → RSI: {rsi_val} | MACD: {macd_hist} → {signal}\n"

    return msg


# ====== FLASK ROUTES ======
@app.route("/")
def home():
    return "Bot is running!", 200


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    # ✅ GET method test
    if request.method == "GET":
        return "Webhook working (GET)", 200

    # ✅ POST method from Telegram
    update = request.get_json()
    print(update)  # Render logs me dikhega

    if not update:
        return "no update", 200

    chat_id = None
    text = None

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text")
    elif "callback_query" in update:
        chat_id = update["callback_query"]["message"]["chat"]["id"]
        text = update["callback_query"]["data"]

    if not chat_id or not text:
        return "ok", 200

    # ====== COMMANDS ======
    if text == "/start":
        buttons = [
            [
                {"text": "📊 Top Coins", "callback_data": "/top"},
                {"text": "💰 BTC Price", "callback_data": "/btc"}
            ],
            [
                {"text": "💰 ETH Price", "callback_data": "/eth"},
                {"text": "📈 Signals", "callback_data": "/signal"}
            ],
            [
                {"text": "🔗 Join Channel", "callback_data": "/join"}
            ],
            [
                {"text": "🛒 Subscribe (Coming Soon)", "callback_data": "/subscribe"}
            ]
        ]
        send_message(chat_id, "👋 Welcome to <b>PrimeKing Crypto Bot</b>\n\nUse commands or buttons below 👇", buttons)

    elif text == "/top":
        send_message(chat_id, get_top_coins())

    elif text == "/btc":
        price = get_price("bitcoin")
        send_message(chat_id, f"💰 Bitcoin (BTC): ${price}")

    elif text == "/eth":
        price = get_price("ethereum")
        send_message(chat_id, f"💰 Ethereum (ETH): ${price}")

    elif text == "/signal":
        coins = ["BTC", "ETH", "BNB", "XRP", "DOGE", "ADA", "SOL", "TRX", "DOT", "MATIC"]
        random.shuffle(coins)
        selected = coins[:3]

        msg = "🚀 <b>Crypto Signals (RSI + MACD)</b>\n\n"
        for coin in selected:
            msg += get_signal(coin) + "\n\n"

        send_message(chat_id, msg)

    elif text == "/join":
        channel_url = "https://t.me/+On10pWG7cbAxNTY1"
        buttons = [[{"text": "👉 Join Channel", "url": channel_url}]]
        msg = "🔗 Click below to join our Telegram channel 👇"
        send_message(chat_id, msg, buttons)

    elif text == "/subscribe":
        buttons = [[{"text": "🛒 Subscribe (Coming Soon)", "callback_data": "/subscribe"}]]
        send_message(chat_id, "🚀 Paid Subscription Feature Coming Soon... Stay tuned!", buttons)

    else:
        send_message(chat_id, "⚠️ Unknown command. Use /start to see available commands.")

    return "ok", 200
