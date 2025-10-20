#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import logging
import requests
from datetime import datetime, timezone
from decimal import Decimal, getcontext, InvalidOperation
from dotenv import load_dotenv

# دقت اعشاری
getcontext().prec = 12

# بارگذاری .env
load_dotenv()
CMC_API_KEY = os.getenv("CMC_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not (CMC_API_KEY and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
    raise SystemExit("⚠️ لطفاً CMC_API_KEY، TELEGRAM_BOT_TOKEN و TELEGRAM_CHAT_ID را وارد کنید.")

CMC_BASE = "https://pro-api.coinmarketcap.com/v1"
TG_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
HEADERS = {"Accepts": "application/json", "X-CMC_PRO_API_KEY": CMC_API_KEY}

# لاگ
logging.basicConfig(
    filename="crypto_bot.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def fetch_top_cryptos(limit=600):
    """📥 دریافت ۶۰۰ ارز برتر با یک درخواست"""
    url = f"{CMC_BASE}/cryptocurrency/listings/latest"
    params = {"limit": limit, "convert": "USDT"}
    r = requests.get(url, headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("data", [])

def format_decimal(d):
    return f"{d:.2f}"

def send_telegram_message(text):
    url = f"{TG_BASE}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        requests.post(url, data=payload, timeout=15)
    except Exception as e:
        logging.error(f"❌ Telegram send error: {e}")

def send_ui_filtered_cryptos():
    logging.info("🚀 شروع تحلیل UI < 5 برای ۶۰۰ ارز")
    cryptos = fetch_top_cryptos(limit=600)
    total_checked = 0
    btc_usdt_list = []
    normal_list = []
    invalid_cryptos = []

    # پردازش داده‌ها
    for item in cryptos:
        total_checked += 1
        symbol = item.get("symbol")
        quote = item.get("quote", {}).get("USDT", {})
        price_str = quote.get("price")
        vol_str = quote.get("volume_24h")
        market_cap_str = quote.get("market_cap")

        try:
            price = Decimal(str(price_str))
            volume = Decimal(str(vol_str))
            market_cap = Decimal(str(market_cap_str))
        except (InvalidOperation, TypeError):
            invalid_cryptos.append(symbol)
            continue

        if volume <= 0 or market_cap <= 0:
            invalid_cryptos.append(symbol)
            continue

        try:
            ui_index = (market_cap / volume).quantize(Decimal("0.01"))
        except InvalidOperation:
            invalid_cryptos.append(symbol)
            continue

        coin_data = {
            "symbol": symbol,
            "price": price,
            "ui": ui_index
        }

        if symbol in ["BTC", "USDT"]:
            btc_usdt_list.append(coin_data)
        elif ui_index < 5:
            normal_list.append(coin_data)

    # مرتب سازی کم به زیاد
    normal_list.sort(key=lambda c: float(c['ui']))

    # ترکیب نهایی با خط جداکننده
    final_list = btc_usdt_list + [{"separator": True}] + normal_list

    # ساخت پیام یکپارچه (Batch بزرگ، کمتر API)
    message_lines = []
    idx_counter = 1
    for coin in final_list:
        if "separator" in coin:
            message_lines.append("─────────────")
        else:
            line = f"{idx_counter}. {coin['symbol']:<7} | {format_decimal(coin['price']):>6} |🧮 {coin['ui']}"
            message_lines.append(line)
            idx_counter += 1

    # ارسال پیام‌ها با طول مناسب (حد اکثر ۲۰۰۰ کاراکتر تلگرام)
    text = ""
    for line in message_lines:
        if len(text) + len(line) + 1 > 1800:  # مرز محافظه‌کار
            send_telegram_message(text)
            text = ""
        text += line + "\n"
    if text:
        send_telegram_message(text)

    # پیام ارزهای ناقص
    if invalid_cryptos:
        invalid_msg = "⚠️ ارزهای ناقص یا نامعتبر:\n" + "\n".join(f"{s}" for s in invalid_cryptos)
        invalid_msg += f"\n🔢 تعداد: {len(invalid_cryptos)}"
        send_telegram_message(invalid_msg)

    # پیام نهایی
    final_msg = (
        f"✅ تحلیل ارزها انجام شد!\n"
        f"📊 تعداد کل ارزهای بررسی شده: {total_checked}\n"
        f"📦 تعداد ارزهای UI < 5 برابر با : {len(normal_list)}\n"
        f"🚫 تعداد ارزهای ناقص: {len(invalid_cryptos)}\n"
        f"⏰ زمان اجرا: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"🔗 داده‌ها از CoinMarketCap"
    )
    send_telegram_message(final_msg)
    logging.info("✅ پیام نهایی ارسال شد.")

if __name__ == "__main__":
    try:
        send_ui_filtered_cryptos()
    except Exception as e:
        logging.exception(f"❌ خطا در اجرای تحلیل: {e}")
