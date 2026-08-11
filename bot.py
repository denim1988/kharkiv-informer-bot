import threading
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run_flask, daemon=True).start()
import time
import requests
import telebot
from telebot import types
from telebot import apihelper

# ==================== НАСТРОЙКА ====================
BOT_TOKEN = "8423812452:AAGUhfeGS9sIY0A_TsbHd3V2ZkA3vS_EeQk"  # Твой токен

# Настройка прокси для PythonAnywhere
# apihelper.proxy = {'https': 'http://proxy.server:3128'}

bot = telebot.TeleBot(BOT_TOKEN)

# Безопасная функция отправки сообщений (защита от лагов прокси)
def safe_send_message(chat_id, text):
    for attempt in range(3):
        try:
            bot.send_message(chat_id, text, parse_mode="HTML", disable_web_page_preview=True)
            break
        except Exception as e:
            print(f"Мигнул прокси при отправке (попытка {attempt+1}/3)...")
            time.sleep(2)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}

PARTNER_FOOTER = '\n\n— — — — — — — — — —\n📢 <b>Наш партнёр:</b> <a href="https://t.me/kuplyu_prodam_kh">Куплю Продам</a>'
#PARTNER_FOOTER = (
#    '\n\n— — — — — — — — — —\n'
#    '🤖 <b>Наш бот:</b> <a href="https://t.me/super_kh_bot">Харьков Информер</a>\n'
#    '📢 <b>Наш партнёр:</b> <a href="https://t.me/kuplyu_prodam_kh">Куплю Продам</a>')

# ==================== 1. ПОГОДА И СОВЕТЫ ====================
def get_weather_with_advice():
    cities = {
        "Харьков": (50.0011, 36.2315),
        "Чугуев": (49.8356, 36.6844),
        "Харьковская область": (49.9935, 36.2304)
    }

    response_text = "🌤 <b>ПОГОДА</b>\n\n"
    temps = []
    winds = []
    rain_expected = False

    for city, (lat, lon) in cities.items():
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&timezone=auto"
            data = requests.get(url, headers=HEADERS, timeout=5).json()
            curr = data.get("current_weather", {})
            temp = curr.get("temperature", 20)
            wind = curr.get("windspeed", 0)
            code = curr.get("weathercode", 0)

            temps.append(temp)
            winds.append(wind)
            if code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
                rain_expected = True

            response_text += f"📍 <b>{city}</b>\n• Температура: {temp}°C\n• Ветер: {wind} км/ч\n\n"
        except Exception:
            response_text += f"📍 <b>{city}</b>: Не удалось получить данные.\n\n"

    if temps:
        avg_temp = sum(temps) / len(temps)
        avg_wind = sum(winds) / len(winds)

        advice = []
        if avg_temp >= 22:
            advice.append("🩳 Легкая летняя одежда: футболка, шорты/лёгкие брюки.")
        elif 15 <= avg_temp < 22:
            advice.append("👕 Умеренно тепло: футболка и лёгкая кофта/ветровка.")
        elif 5 <= avg_temp < 15:
            advice.append("🧥 Прохладно: надевай куртку или тёплый свитер.")
        else:
            advice.append("🥶 Холодно: тёплая куртка, шапка.")

        if avg_wind > 15:
            advice.append("💨 Сильный ветер.")
        if rain_expected:
            advice.append("☔ Ожидается дождь — возьми зонт!")

        advice_str = " ".join(advice)
        response_text += f"💡 <b>Совет по одежде:</b> {advice_str}"

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

    # 2. Злотый (PLN) из НБУ
    try:
        res_pln = requests.get("https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=PLN&json", timeout=5).json()
        if res_pln:
            pln_rate = round(float(res_pln[0].get('rate')), 2)
            text += f"🇵🇱 <b>PLN/UAH (Злотый):</b> 1 PLN = {pln_rate} грн (НБУ)\n"
    except Exception:
        text += "🇵🇱 <b>PLN/UAH:</b> Ошибка загрузки\n"

    # 3. Юань (CNY) из НБУ
    try:
        res_cny = requests.get("https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=CNY&json", timeout=5).json()
        if res_cny:
            cny_rate = round(float(res_cny[0].get('rate')), 2)
            text += f"🇨🇳 <b>CNY/UAH (Юань):</b> 1 CNY = {cny_rate} грн (НБУ)\n"
    except Exception:
        text += "🇨🇳 <b>CNY/UAH:</b> Ошибка загрузки\n"

    text += "\n🪙 <b>Криптовалюты (USD):</b>\n"

    # 4. Крипта через CoinGecko
    try:
        crypto_url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd"
        res_crypto = requests.get(crypto_url, headers=HEADERS, timeout=5).json()

        btc_price = res_crypto.get('bitcoin', {}).get('usd', 0)
        eth_price = res_crypto.get('ethereum', {}).get('usd', 0)
        sol_price = res_crypto.get('solana', {}).get('usd', 0)

        text += f"• <b>BTC (Bitcoin):</b> ${btc_price:,.2f}\n"
        text += f"• <b>ETH (Ethereum):</b> ${eth_price:,.2f}\n"
        text += f"• <b>SOL (Solana):</b> ${sol_price:,.2f}\n"
    except Exception:
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
            print(f"Мигнул прокси ({e}), перезапуск через 3 сек...")
            time.sleep(3)
