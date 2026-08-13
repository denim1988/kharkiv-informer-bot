import threading
import time
import os
from flask import Flask
import requests
import telebot
from telebot import types

# ==================== Flask для Render ====================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run_flask, daemon=True).start()

# ==================== НАСТРОЙКА ====================
# Токен подтягивается из Render (Environment Variables) или берется дефолтный
BOT_TOKEN = os.getenv("BOT_TOKEN", "8423812452:AAGUhfeGS9sIY0A_TsbHd3V2ZkA3vS_EeQk")

bot = telebot.TeleBot(BOT_TOKEN)

# Безопасная функция отправки сообщений
def safe_send_message(chat_id, text):
    for attempt in range(3):
        try:
            bot.send_message(chat_id, text, parse_mode="HTML", disable_web_page_preview=True)
            break
        except Exception as e:
            print(f"Ошибка отправки (попытка {attempt+1}/3): {e}")
            time.sleep(2)

PARTNER_FOOTER = '\n\n— — — — — — — — — —\n📢 <b>Наш партнёр:</b> <a href="https://t.me/kuplyu_prodam_kh">Куплю Продам</a>'

# ==================== 1. ПОГОДА И СОВЕТЫ ====================
def get_weather_with_advice():
    response_text = "🌤 <b>ПОГОДА</b>\n\n"

    cities = {
        "Харьков": (50.0011, 36.2315),
        "Чугуев": (49.8356, 36.6844),
        "Харьковская область": (49.9935, 36.2304)
    }

    temps = []
    winds = []
    rain_expected = False

    for city, (lat, lon) in cities.items():
        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,wind_speed_10m,weather_code"
                f"&timezone=auto"
            )

            res = requests.get(url, timeout=10)
            res.raise_for_status()
            data = res.json()

            curr = data.get("current", {})

            temp = round(float(curr.get("temperature_2m", 0)))
            wind = round(float(curr.get("wind_speed_10m", 0)))
            code = int(curr.get("weather_code", 0))

            temps.append(temp)
            winds.append(wind)

            # Дождь / морось / ливень / гроза
            if code in [51, 53, 55, 56, 57,
                        61, 63, 65, 66, 67,
                        80, 81, 82,
                        95, 96, 99]:
                rain_expected = True

            response_text += (
                f"📍 <b>{city}</b>\n"
                f"• Температура: {temp}°C\n"
                f"• Ветер: {wind} км/ч\n\n"
            )

        except Exception as e:
            print(f"Ошибка загрузки погоды ({city}): {e}")
            response_text += (
                f"📍 <b>{city}</b>: Не удалось получить данные\n\n"
            )

    # Формируем совет по одежде
    if temps:
        avg_temp = sum(temps) / len(temps)
        avg_wind = sum(winds) / len(winds)

        advice = []

        if avg_temp >= 22:
            advice.append(
                "🩳 Легкая летняя одежда: футболка, шорты/лёгкие брюки."
            )
        elif 15 <= avg_temp < 22:
            advice.append(
                "👕 Умеренно тепло: футболка и лёгкая кофта/ветровка."
            )
        elif 5 <= avg_temp < 15:
            advice.append(
                "🧥 Прохладно: надевай куртку или тёплый свитер."
            )
        else:
            advice.append(
                "🥶 Холодно: тёплая куртка, шапка."
            )

        if avg_wind > 15:
            advice.append("💨 Сильный ветер.")

        if rain_expected:
            advice.append("☔ Ожидается дождь — возьми зонт!")

        advice_str = " ".join(advice)

        response_text += (
            f"💡 <b>Совет по одежде:</b> {advice_str}"
        )

    return response_text + PARTNER_FOOTER

# ==================== 2. КУРСЫ ВАЛЮТ И КРИПТЫ ====================
def get_currency_rates():
    text = "💵 <b>КУРСЫ ВАЛЮТ И КРИПТОВАЛЮТ</b>\n\n"

    # 1. USD из ПриватБанка
    try:
        res = requests.get("https://api.privatbank.ua/p24api/pubinfo?json&exchange&coursid=5", timeout=5).json()
        for item in res:
            if item.get('ccy') == 'USD':
                buy = round(float(item.get('buy')), 2)
                sale = round(float(item.get('sale')), 2)
                text += f"🇺🇸 <b>USD/UAH:</b> Покупка {buy} грн | Продажа {sale} грн\n"
    except Exception:
        text += "🇺🇸 <b>USD/UAH:</b> Ошибка загрузки\n"

    # 2. Евро (EUR) из НБУ
    try:
        res_eur = requests.get("https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=EUR&json", timeout=5).json()
        if res_eur:
            eur_rate = round(float(res_eur[0].get('rate')), 2)
            text += f"🇪🇺 <b>EUR/UAH (Евро):</b> 1 EUR = {eur_rate} грн (НБУ)\n"
    except Exception:
        text += "🇪🇺 <b>EUR/UAH:</b> Ошибка загрузки\n"

    # 3. Злотый (PLN) из НБУ
    try:
        res_pln = requests.get("https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=PLN&json", timeout=5).json()
        if res_pln:
            pln_rate = round(float(res_pln[0].get('rate')), 2)
            text += f"🇵🇱 <b>PLN/UAH (Злотый):</b> 1 PLN = {pln_rate} грн (НБУ)\n"
    except Exception:
        text += "🇵🇱 <b>PLN/UAH:</b> Ошибка загрузки\n"

    # 4. Юань (CNY) из НБУ
    try:
        res_cny = requests.get("https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=CNY&json", timeout=5).json()
        if res_cny:
            cny_rate = round(float(res_cny[0].get('rate')), 2)
            text += f"🇨🇳 <b>CNY/UAH (Юань):</b> 1 CNY = {cny_rate} грн (НБУ)\n"
    except Exception:
        text += "🇨🇳 <b>CNY/UAH:</b> Ошибка загрузки\n"

    text += "\n🪙 <b>Криптовалюты (USD):</b>\n"

    # 5. Криптовалюты (Bybit -> MEXC)
    btc_price, eth_price, sol_price, xrp_price = 0.0, 0.0, 0.0, 0.0

    try:
        req_btc = requests.get("https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT", timeout=3).json()
        req_eth = requests.get("https://api.bybit.com/v5/market/tickers?category=spot&symbol=ETHUSDT", timeout=3).json()
        req_sol = requests.get("https://api.bybit.com/v5/market/tickers?category=spot&symbol=SOLUSDT", timeout=3).json()
        req_xrp = requests.get("https://api.bybit.com/v5/market/tickers?category=spot&symbol=XRPUSDT", timeout=3).json()

        btc_price = float(req_btc['result']['list'][0]['lastPrice'])
        eth_price = float(req_eth['result']['list'][0]['lastPrice'])
        sol_price = float(req_sol['result']['list'][0]['lastPrice'])
        xrp_price = float(req_xrp['result']['list'][0]['lastPrice'])
    except Exception:
        try:
            req_btc = requests.get("https://api.mexc.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=3).json()
            req_eth = requests.get("https://api.mexc.com/api/v3/ticker/price?symbol=ETHUSDT", timeout=3).json()
            req_sol = requests.get("https://api.mexc.com/api/v3/ticker/price?symbol=SOLUSDT", timeout=3).json()
            req_xrp = requests.get("https://api.mexc.com/api/v3/ticker/price?symbol=XRPUSDT", timeout=3).json()

            btc_price = float(req_btc['price'])
            eth_price = float(req_eth['price'])
            sol_price = float(req_sol['price'])
            xrp_price = float(req_xrp['price'])
        except Exception:
            pass

    if btc_price > 0:
        text += f"• <b>BTC (Bitcoin):</b> ${btc_price:,.2f}\n"
        text += f"• <b>ETH (Ethereum):</b> ${eth_price:,.2f}\n"
        text += f"• <b>SOL (Solana):</b> ${sol_price:,.2f}\n"
        text += f"• <b>XRP (Ripple):</b> ${xrp_price:,.4f}\n"
    else:
        text += "• Не удалось загрузить курсы криптовалют\n"

    return text + PARTNER_FOOTER

# ==================== 3. ПРАВОСЛАВИЕ ====================
def get_orthodox_info():
    text = "☦️ <b>ПРАВОСЛАВИЕ</b>\n\n"
    text += "📖 <b>Православные ресурсы и календарь:</b>\n"
    text += "• <a href=\"https://azbyka.ru/\">Православный портал (Азбука)</a>\n"
    text += "• <a href=\"https://church.ua/\">Сайт УПЦ (офиц.)</a>\n"
    text += "• <a href=\"https://t.me/upc_news\">Официальный Telegram УПЦ</a>\n\n"
    text += "💡 <i>Перейдите по ссылкам для чтения Евангелия дня, молитв и новостей.</i>"
    return text + PARTNER_FOOTER

# ==================== 4. АФИША ХАРЬКОВ ====================
def get_kharkiv_events():
    text = "🎭 <b>АФИША ХАРЬКОВ</b>\n\n"
    text += "🎟 <b>Спектакли, Концерты, Шоу и Театры:</b>\n"
    text += "• <a href=\"https://kharkiv.internet-bilet.ua/\">Афиша Internet-Bilet</a>\n"
    text += "• <a href=\"https://kharkiv.karabas.com/ru/\">Афиша Karabas</a>\n\n"
    text += "🎬 <b>Кинотеатр Multiplex в ТРЦ Никольский:</b>\n"
    text += "• <a href=\"https://multiplex.ua/cinema/kharkiv/nikolsky\">Расписание сеансов и билеты</a>\n\n"
    text += "💡 <i>Нажмите на нужную ссылку, чтобы открыть расписание и купить билеты.</i>"
    return text + PARTNER_FOOTER

# ==================== ОБРАБОТКА КОМАНД И КНОПОК ====================
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("🌤 Погода")
    btn2 = types.KeyboardButton("💵 Курс валют")
    btn3 = types.KeyboardButton("☦️ Православие")
    btn4 = types.KeyboardButton("🎭 Афиша Харьков")
    markup.add(btn1, btn2, btn3, btn4)
    bot.send_message(message.chat.id, "Приветствует Харьков Информер!", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    text = message.text.lower() if message.text else ""

    if "погода" in text:
        res = get_weather_with_advice()
        safe_send_message(message.chat.id, res)

    elif "курс" in text or "валют" in text:
        res = get_currency_rates()
        safe_send_message(message.chat.id, res)

    elif "православие" in text:
        res = get_orthodox_info()
        safe_send_message(message.chat.id, res)

    elif "афиша" in text:
        res = get_kharkiv_events()
        safe_send_message(message.chat.id, res)

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    print("Бот запущен!")
    while True:
        try:
            bot.polling(none_stop=True, interval=2, timeout=15)
        except Exception as e:
            print(f"Ошибка соединения ({e}), перезапуск через 3 сек...")
            time.sleep(3)
