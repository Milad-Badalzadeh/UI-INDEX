#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import requests
from datetime import datetime, timezone
from decimal import Decimal, getcontext
from dotenv import load_dotenv

# دقت محاسبات اعشاری
getcontext().prec = 12

# بارگذاری مقادیر از .env
load_dotenv()

CMC_API_KEY = os.getenv("CMC_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not (CMC_API_KEY and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
    raise SystemExit("⚠️ لطفاً مقادیر CMC_API_KEY، TELEGRAM_BOT_TOKEN و TELEGRAM_CHAT_ID را در فایل .env وارد کنید.")

CMC_BASE = "https://pro-api.coinmarketcap.com/v1"
TG_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

HEADERS = {
    "Accepts": "application/json",
    "X-CMC_PRO_API_KEY": CMC_API_KEY
}


def fetch_top_cryptos(limit=200):
    """📥 دریافت ۲۰۰ ارز برتر"""
    url = f"{CMC_BASE}/cryptocurrency/listings/latest"
    params = {"limit": limit, "convert": "USDT"}
    r = requests.get(url, headers=HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def format_decimal(d):
    """🎯 نمایش عدد با دو رقم اعشار"""
    return f"{d:,.2f}"


def build_message(symbol, item, ui_index):
    """🧾 ساخت پیام خلاصه برای هر ارز"""
    quote = item.get("quote", {}).get("USDT", {})
    price = Decimal(str(quote.get("price", 0)))
    vol_24h = Decimal(str(quote.get("volume_24h", 0)))
    market_cap = Decimal(str(quote.get("market_cap", 0)))

    msg = (
        f"💰 {symbol}/USDT\n"
        f"💵 Price: {format_decimal(price)} USDT\n"
        f"🏦 Market Cap: {format_decimal(market_cap)} USDT\n"
        f"📊 24H Volume: {format_decimal(vol_24h)} USDT\n"
        f"🧮 UI Index (MC/Vol24h): {ui_index}\n"
        "────────────────────────"
    )
    return msg


def send_telegram_message(text):
    """📤 ارسال پیام به تلگرام"""
    url = f"{TG_BASE}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    requests.post(url, data=payload, timeout=10)


def send_crypto_updates():
    """🚀 اجرای تحلیل و ارسال پیام‌ها"""
    data = fetch_top_cryptos(limit=200)
    cryptos = data.get("data", [])

    low_ui_list = []  # برای ذخیره ارزهای UI < 5

    for idx, item in enumerate(cryptos, 1):
        symbol = item.get("symbol")
        quote = item.get("quote", {}).get("USDT", {})

        market_cap = Decimal(str(quote.get("market_cap", 0)))
        vol_24h = Decimal(str(quote.get("volume_24h", 0)))

        if vol_24h == 0:
            continue

        ui_index = (market_cap / vol_24h).quantize(Decimal("0.01"))
        msg = build_message(symbol, item, ui_index)

        send_telegram_message(msg)
        print(f"📤 Sent {idx}: {symbol} (UI={ui_index})")
        time.sleep(1)

        if ui_index < 5:
            low_ui_list.append((symbol, ui_index))

    # ساخت پیام نهایی
    if low_ui_list:
        final_msg = "⚠️ به اینا توجه کنید 👇\n🔥 ارزهایی با UI Index کمتر از 5:\n\n"
        final_msg += "━━━━━━━━━━━━━━━━━━\n"
        final_msg += "💰 SYMBOL    📊 UI Index\n"
        final_msg += "━━━━━━━━━━━━━━━━━━\n"

        for sym, ui in low_ui_list:
            final_msg += f"{sym:<10} {ui}\n"

        final_msg += "━━━━━━━━━━━━━━━━━━\n"
        final_msg += f"⏰ زمان اجرا: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"

        send_telegram_message(final_msg)
        print("✅ پیام نهایی ارزهای مهم ارسال شد.")
    else:
        send_telegram_message("ℹ️ هیچ ارزی با UI Index کمتر از 5 پیدا نشد.")
        print("ℹ️ هیچ ارز با UI Index پایین پیدا نشد.")


if __name__ == "__main__":
    INTERVAL_SECONDS = 18000  # هر ۵ ساعت

    while True:
        print("🚀 اجرای تحلیل جدید...")
        send_crypto_updates()
        print(f"🕒 در حال انتظار برای {INTERVAL_SECONDS/3600} ساعت بعد...")
        time.sleep(INTERVAL_SECONDS)
