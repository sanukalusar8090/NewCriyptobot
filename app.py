from flask import Flask, request
import requests, os

app = Flask(__name__)

TOKEN = os.getenv("BOT_TOKEN")
CG_API_KEY = os.getenv("CG_API_KEY")
TAAPI_KEY = os.getenv("TAAPI_KEY")
API_URL = f"https://api.telegram.org/bot{TOKEN}/"


def send_message(chat_id, text, buttons=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    requests.post(API_URL + "sendMessage", json=payload)


def get_price(symbol):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd"
    headers = {"x-cg-demo-api-key": CG_API_KEY}
    data = requests.get(url, headers=headers).json()
    return data.get(symbol, {}).get("usd", 0)


def get_top_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=50&page=1&sparkline=false&price_change_percentage=24h"
    headers = {"x-cg-demo-api-key": CG_API_KEY}
    data = requests.get(url, headers=headers).json()
    if not data:
        return "⚠️ Error fetching data."
    gainers = sorted(data, key=lambda x: x.get("price_change_percentage_24h", 0), reverse=True)[:5]
    losers = sorted(data, key=lambda x: x.get("price_change_percentage_24h", 0))[:5]
    msg = "📊 <b>Top 5 Gainers</b>\n"
    for c in gainers:
        msg += f"✅ {c['name']} ({c['symbol'].upper()}) +{round(c['price_change_percentage_24h'],2)}%\n"
    msg += "\n📉 <b>Top 5 Losers</b>\n"
    for c in losers:
        msg += f"❌ {c['name']} ({c['symbol'].upper()}) {round(c['price_change_percentage_24h'],2)}%\n"
    return msg


def get_signal(symbol):
    intervals = ["1h", "4h", "1d"]
    msg = f"📊 <b>Signal for {symbol}</b>\n"
    for intv in intervals:
        url_rsi = f"https://api.taapi.io/rsi?secret={TAAPI_KEY}&exchange=binance&symbol={symbol}/USDT&interval={intv}"
        url_macd = f"https://api.taapi.io/macd?secret={TAAPI_KEY}&exchange=binance&symbol={symbol}/USDT&interval={intv}"
        rsi = requests.get(url_rsi).json().get("value", 0)
        macd_hist = requests.get(url_macd).json().get("valueMACDHist", 0)
        if rsi < 30 and macd_hist > 0:
            signal = "🟢 Strong Buy"
        elif rsi > 70 and macd_hist < 0:
            signal = "🔴 Strong Sell"
        else:
            signal = "⚪ Neutral"
        msg += f"⏱ {intv} → RSI: {rsi} | MACD: {macd_hist} → {signal}\n"
    return msg


@app.route("/", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update:
        return "ok"

    chat_id = update.get("message", {}).get("chat", {}).get("id") or               update.get("callback_query", {}).get("message", {}).get("chat", {}).get("id")
    text = update.get("message", {}).get("text") or update.get("callback_query", {}).get("data")

    if not chat_id or not text:
        return "ok"

    if text == "/start":
        buttons = [
            [{"text": "📊 Top Coins", "callback_data": "/top"}, {"text": "💰 BTC Price", "callback_data": "/btc"}],
            [{"text": "💰 ETH Price", "callback_data": "/eth"}, {"text": "📈 Signals", "callback_data": "/signal"}],
            [{"text": "🔗 Join Channel", "callback_data": "/join"}],
            [{"text": "🛒 Subscribe (Coming Soon)", "callback_data": "/subscribe"}]
        ]
        send_message(chat_id, "👋 Welcome to <b>PrimeKing Crypto Bot</b>\n\nUse commands or buttons below 👇", buttons)

    elif text == "/top":
        send_message(chat_id, get_top_coins())

    elif text == "/btc":
        send_message(chat_id, f"💰 Bitcoin (BTC): ${get_price('bitcoin')}")

    elif text == "/eth":
        send_message(chat_id, f"💰 Ethereum (ETH): ${get_price('ethereum')}")

    elif text == "/signal":
        import random
        coins = ["BTC","ETH","BNB","XRP","DOGE","ADA","SOL","TRX","DOT","MATIC"]
        random.shuffle(coins)
        selected = coins[:3]
        msg = "🚀 <b>Crypto Signals (RSI + MACD)</b>\n\n"
        for coin in selected:
            msg += get_signal(coin) + "\n\n"
        send_message(chat_id, msg)

    elif text == "/join":
        channel_url = "https://t.me/+On10pWG7cbAxNTY1"
        buttons = [[{"text": "👉 Join Channel", "url": channel_url}]]
        send_message(chat_id, "🔗 Click below to join our Telegram channel 👇", buttons)

    elif text == "/subscribe":
        buttons = [[{"text": "🛒 Subscribe (Coming Soon)", "callback_data": "/subscribe"}]]
        send_message(chat_id, "🚀 Paid Subscription Feature Coming Soon... Stay tuned!", buttons)

    else:
        send_message(chat_id, "⚠️ Unknown command. Use /start to see available commands.")

    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
