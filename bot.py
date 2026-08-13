import threading
import time
import os

from flask import Flask
import requests
import telebot
from telebot import types


# ============================================================
# 1. FLASK ДЛЯ RENDER
# ============================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Bot is running!"


def run_flask():
    app.run(host="0.0.0.0", port=8080)


threading.Thread(target=run_flask, daemon=True).start()


# ============================================================
# 2. НАСТРОЙКА TELEGRAM
# ============================================================

# Токен ОБЯЗАТЕЛЬНО должен быть в Render:
# Environment -> Environment Variables -> BOT_TOKEN

BOT_TOKEN = os.getenv("8423812452:AAGUhfeGS9sIY0A_TsbHd3V2ZkA3vS_EeQk")

if not BOT_TOKEN:
    raise RuntimeError(
        "Не найден BOT_TOKEN. Добавь BOT_TOKEN в Environment Variables на Render."
    )

bot = telebot.TeleBot(BOT_TOKEN)


# ============================================================
# 3. БЕЗОПАСНАЯ ОТПРАВКА СООБЩЕНИЙ
# ============================================================

def safe_send_message(chat_id, text):
    for attempt in range(3):
        try:
            bot.send_message(
                chat_id,
                text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            return

        except Exception as e:
            print(
                f"[TELEGRAM] Ошибка отправки "
                f"(попытка {attempt + 1}/3): {e}"
            )
            time.sleep(2)


# ============================================================
# 4. ПОДВАЛ
# ============================================================

PARTNER_FOOTER = (
    "\n\n"
    "— — — — — — — — — —\n"
    "📢 <b>Наш партнёр:</b> "
    '<a href="https://t.me/kuplyu_prodam_kh">Куплю Продам</a>'
)


# ============================================================
# 5. ПОГОДА И СОВЕТЫ
# ============================================================

def get_weather_with_advice():

    print("[ПОГОДА] Начинаю получение погоды...")

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

            print(f"[ПОГОДА] Запрашиваю данные для: {city}")

            url = (
                "https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat}"
                f"&longitude={lon}"
                "&current=temperature_2m,wind_speed_10m,weather_code"
                "&temperature_unit=celsius"
                "&wind_speed_unit=kmh"
                "&timezone=auto"
            )

            print(f"[ПОГОДА] URL для {city}: {url}")

            # Запрос к Open-Meteo
            res = requests.get(url, timeout=10)

            print(
                f"[ПОГОДА] {city} HTTP статус: {res.status_code}"
            )

            # Если сервер вернул ошибку
            res.raise_for_status()

            # Получаем JSON
            data = res.json()

            print(
                f"[ПОГОДА] Ответ Open-Meteo для {city}: {data}"
            )

            # Получаем блок current
            curr = data.get("current")

            if not curr:
                raise ValueError(
                    f"Open-Meteo не вернул блок current: {data}"
                )

            print(
                f"[ПОГОДА] current для {city}: {curr}"
            )

            # Получаем необходимые значения
            temp_value = curr.get("temperature_2m")
            wind_value = curr.get("wind_speed_10m")
            code_value = curr.get("weather_code")

            # НЕ подставляем нули.
            # Если данных нет — вызываем ошибку.
            if temp_value is None:
                raise ValueError(
                    f"Нет temperature_2m: {curr}"
                )

            if wind_value is None:
                raise ValueError(
                    f"Нет wind_speed_10m: {curr}"
                )

            if code_value is None:
                raise ValueError(
                    f"Нет weather_code: {curr}"
                )

            # Преобразуем данные
            temp = round(float(temp_value))
            wind = round(float(wind_value))
            code = int(code_value)

            print(
                f"[ПОГОДА] {city}: "
                f"{temp}°C, ветер {wind} км/ч, код {code}"
            )

            # Сохраняем для среднего значения
            temps.append(temp)
            winds.append(wind)

            # Коды дождя / мороси / ливней / грозы
            if code in [
                51, 53, 55,
                56, 57,
                61, 63, 65,
                66, 67,
                80, 81, 82,
                95, 96, 99
            ]:
                rain_expected = True

            # Добавляем город в сообщение
            response_text += (
                f"📍 <b>{city}</b>\n"
                f"• Температура: {temp}°C\n"
                f"• Ветер: {wind} км/ч\n\n"
            )

        except Exception as e:

            print(
                f"[ОШИБКА ПОГОДЫ] {city}: {e}"
            )

            response_text += (
                f"📍 <b>{city}</b>\n"
                f"• ⚠️ Не удалось получить данные\n\n"
            )

    # ========================================================
    # СОВЕТ ПО ОДЕЖДЕ
    # ========================================================

    if temps:

        avg_temp = sum(temps) / len(temps)
        avg_wind = sum(winds) / len(winds)

        advice = []

        if avg_temp >= 22:

            advice.append(
                "🩳 Легкая летняя одежда: "
                "футболка, шорты/лёгкие брюки."
            )

        elif 15 <= avg_temp < 22:

            advice.append(
                "👕 Умеренно тепло: "
                "футболка и лёгкая кофта/ветровка."
            )

        elif 5 <= avg_temp < 15:

            advice.append(
                "🧥 Прохладно: "
                "надевай куртку или тёплый свитер."
            )

        else:

            advice.append(
                "🥶 Холодно: "
                "тёплая куртка, шапка."
            )

        if avg_wind > 15:
            advice.append("💨 Сильный ветер.")

        if rain_expected:
            advice.append(
                "☔ Ожидается дождь — возьми зонт!"
            )

        advice_str = " ".join(advice)

        response_text += (
            f"💡 <b>Совет по одежде:</b> "
            f"{advice_str}"
        )

    else:

        response_text += (
            "⚠️ <b>Не удалось получить данные о погоде.</b>"
        )

    print("[ПОГОДА] Формирование сообщения завершено.")

    return response_text + PARTNER_FOOTER


# ============================================================
# 6. КУРСЫ ВАЛЮТ И КРИПТОВАЛЮТ
# ============================================================

def get_currency_rates():

    text = "💵 <b>КУРСЫ ВАЛЮТ И КРИПТОВАЛЮТ</b>\n\n"

    # --------------------------------------------------------
    # USD — ПриватБанк
    # --------------------------------------------------------

    try:

        res = requests.get(
            "https://api.privatbank.ua/p24api/pubinfo?json&exchange&coursid=5",
            timeout=5
        )

        data = res.json()

        for item in data:

            if item.get("ccy") == "USD":

                buy = round(
                    float(item.get("buy")),
                    2
                )

                sale = round(
                    float(item.get("sale")),
                    2
                )

                text += (
                    f"🇺🇸 <b>USD/UAH:</b> "
                    f"Покупка {buy} грн | "
                    f"Продажа {sale} грн\n"
                )

    except Exception as e:

        print(
            f"[ВАЛЮТА] Ошибка USD: {e}"
        )

        text += (
            "🇺🇸 <b>USD/UAH:</b> "
            "Ошибка загрузки\n"
        )

    # --------------------------------------------------------
    # EUR — НБУ
    # --------------------------------------------------------

    try:

        res_eur = requests.get(
            "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=EUR&json",
            timeout=5
        )

        data_eur = res_eur.json()

        if data_eur:

            eur_rate = round(
                float(data_eur[0].get("rate")),
                2
            )

            text += (
                f"🇪🇺 <b>EUR/UAH (Евро):</b> "
                f"1 EUR = {eur_rate} грн (НБУ)\n"
            )

    except Exception as e:

        print(
            f"[ВАЛЮТА] Ошибка EUR: {e}"
        )

        text += (
            "🇪🇺 <b>EUR/UAH:</b> "
            "Ошибка загрузки\n"
        )

    # --------------------------------------------------------
    # PLN — НБУ
    # --------------------------------------------------------

    try:

        res_pln = requests.get(
            "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=PLN&json",
            timeout=5
        )

        data_pln = res_pln.json()

        if data_pln:

            pln_rate = round(
                float(data_pln[0].get("rate")),
                2
            )

            text += (
                f"🇵🇱 <b>PLN/UAH (Злотый):</b> "
                f"1 PLN = {pln_rate} грн (НБУ)\n"
            )

    except Exception as e:

        print(
            f"[ВАЛЮТА] Ошибка PLN: {e}"
        )

        text += (
            "🇵🇱 <b>PLN/UAH:</b> "
            "Ошибка загрузки\n"
        )

    # --------------------------------------------------------
    # CNY — НБУ
    # --------------------------------------------------------

    try:

        res_cny = requests.get(
            "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=CNY&json",
            timeout=5
        )

        data_cny = res_cny.json()

        if data_cny:

            cny_rate = round(
                float(data_cny[0].get("rate")),
                2
            )

            text += (
                f"🇨🇳 <b>CNY/UAH (Юань):</b> "
                f"1 CNY = {cny_rate} грн (НБУ)\n"
            )

    except Exception as e:

        print(
            f"[ВАЛЮТА] Ошибка CNY: {e}"
        )

        text += (
            "🇨🇳 <b>CNY/UAH:</b> "
            "Ошибка загрузки\n"
        )

    # --------------------------------------------------------
    # Криптовалюты
    # --------------------------------------------------------

    text += "\n🪙 <b>Криптовалюты (USD):</b>\n"

    btc_price = 0.0
    eth_price = 0.0
    sol_price = 0.0
    xrp_price = 0.0

    # --------------------------------------------------------
    # Bybit
    # --------------------------------------------------------

    try:

        req_btc = requests.get(
            "https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT",
            timeout=3
        ).json()

        req_eth = requests.get(
            "https://api.bybit.com/v5/market/tickers?category=spot&symbol=ETHUSDT",
            timeout=3
        ).json()

        req_sol = requests.get(
            "https://api.bybit.com/v5/market/tickers?category=spot&symbol=SOLUSDT",
            timeout=3
        ).json()

        req_xrp = requests.get(
            "https://api.bybit.com/v5/market/tickers?category=spot&symbol=XRPUSDT",
            timeout=3
        ).json()

        btc_price = float(
            req_btc["result"]["list"][0]["lastPrice"]
        )

        eth_price = float(
            req_eth["result"]["list"][0]["lastPrice"]
        )

        sol_price = float(
            req_sol["result"]["list"][0]["lastPrice"]
        )

        xrp_price = float(
            req_xrp["result"]["list"][0]["lastPrice"]
        )

    except Exception as e:

        print(
            f"[КРИПТО] Bybit ошибка: {e}"
        )

        # ----------------------------------------------------
        # MEXC — резерв
        # ----------------------------------------------------

        try:

            req_btc = requests.get(
                "https://api.mexc.com/api/v3/ticker/price?symbol=BTCUSDT",
                timeout=3
            ).json()

            req_eth = requests.get(
                "https://api.mexc.com/api/v3/ticker/price?symbol=ETHUSDT",
                timeout=3
            ).json()

            req_sol = requests.get(
                "https://api.mexc.com/api/v3/ticker/price?symbol=SOLUSDT",
                timeout=3
            ).json()

            req_xrp = requests.get(
                "https://api.mexc.com/api/v3/ticker/price?symbol=XRPUSDT",
                timeout=3
            ).json()

            btc_price = float(
                req_btc["price"]
            )

            eth_price = float(
                req_eth["price"]
            )

            sol_price = float(
                req_sol["price"]
            )

            xrp_price = float(
                req_xrp["price"]
            )

        except Exception as e:

            print(
                f"[КРИПТО] MEXC ошибка: {e}"
            )

    if btc_price > 0:

        text += (
            f"• <b>BTC (Bitcoin):</b> "
            f"${btc_price:,.2f}\n"
        )

        text += (
            f"• <b>ETH (Ethereum):</b> "
            f"${eth_price:,.2f}\n"
        )

        text += (
            f"• <b>SOL (Solana):</b> "
            f"${sol_price:,.2f}\n"
        )

        text += (
            f"• <b>XRP (Ripple):</b> "
            f"${xrp_price:,.4f}\n"
        )

    else:

        text += (
            "• Не удалось загрузить "
            "курсы криптовалют\n"
        )

    return text + PARTNER_FOOTER


# ============================================================
# 7. ПРАВОСЛАВИЕ
# ============================================================

def get_orthodox_info():

    text = (
        "☦️ <b>ПРАВОСЛАВИЕ</b>\n\n"
    )

    text += (
        "📖 <b>Православные ресурсы и календарь:</b>\n"
    )

    text += (
        '• <a href="https://azbyka.ru/">'
        "Православный портал (Азбука)</a>\n"
    )

    text += (
        '• <a href="https://church.ua/">'
        "Сайт УПЦ (офиц.)</a>\n"
    )

    text += (
        '• <a href="https://t.me/upc_news">'
        "Официальный Telegram УПЦ</a>\n\n"
    )

    text += (
        "💡 <i>Перейдите по ссылкам "
        "для чтения Евангелия дня, "
        "молитв и новостей.</i>"
    )

    return text + PARTNER_FOOTER


# ============================================================
# 8. АФИША ХАРЬКОВА
# ============================================================

def get_kharkiv_events():

    text = (
        "🎭 <b>АФИША ХАРЬКОВ</b>\n\n"
    )

    text += (
        "🎟 <b>Спектакли, Концерты, "
        "Шоу и Театры:</b>\n"
    )

    text += (
        '• <a href="https://kharkiv.internet-bilet.ua/">'
        "Афиша Internet-Bilet</a>\n"
    )

    text += (
        '• <a href="https://kharkiv.karabas.com/ru/">'
        "Афиша Karabas</a>\n\n"
    )

    text += (
        "🎬 <b>Кинотеатр Multiplex "
        "в ТРЦ Никольский:</b>\n"
    )

    text += (
        '• <a href="https://multiplex.ua/cinema/kharkiv/nikolsky">'
        "Расписание сеансов и билеты</a>\n\n"
    )

    text += (
        "💡 <i>Нажмите на нужную ссылку, "
        "чтобы открыть расписание "
        "и купить билеты.</i>"
    )

    return text + PARTNER_FOOTER


# ============================================================
# 9. КОМАНДА /START
# ============================================================

@bot.message_handler(commands=["start"])
def start(message):

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        row_width=2
    )

    btn1 = types.KeyboardButton("🌤 Погода")
    btn2 = types.KeyboardButton("💵 Курс валют")
    btn3 = types.KeyboardButton("☦️ Православие")
    btn4 = types.KeyboardButton("🎭 Афиша Харьков")

    markup.add(
        btn1,
        btn2,
        btn3,
        btn4
    )

    bot.send_message(
        message.chat.id,
        "Приветствует Харьков Информер!",
        reply_markup=markup
    )


# ============================================================
# 10. ОБРАБОТКА КНОПОК
# ============================================================

@bot.message_handler(func=lambda message: True)
def handle_buttons(message):

    text = (
        message.text.lower()
        if message.text
        else ""
    )

    # --------------------------------------------------------
    # ПОГОДА
    # --------------------------------------------------------

    if "погода" in text:

        print(
            f"[TELEGRAM] Пользователь "
            f"{message.chat.id} запросил погоду"
        )

        try:

            res = get_weather_with_advice()

            safe_send_message(
                message.chat.id,
                res
            )

        except Exception as e:

            print(
                f"[ПОГОДА] Критическая ошибка: {e}"
            )

            safe_send_message(
                message.chat.id,
                "⚠️ Не удалось загрузить погоду. "
                "Попробуйте ещё раз."
            )

    # --------------------------------------------------------
    # КУРС ВАЛЮТ
    # --------------------------------------------------------

    elif "курс" in text or "валют" in text:

        try:

            res = get_currency_rates()

            safe_send_message(
                message.chat.id,
                res
            )

        except Exception as e:

            print(
                f"[ВАЛЮТА] Критическая ошибка: {e}"
            )

            safe_send_message(
                message.chat.id,
                "⚠️ Не удалось загрузить курсы."
            )

    # --------------------------------------------------------
    # ПРАВОСЛАВИЕ
    # --------------------------------------------------------

    elif "православие" in text:

        res = get_orthodox_info()

        safe_send_message(
            message.chat.id,
            res
        )

    # --------------------------------------------------------
    # АФИША
    # --------------------------------------------------------

    elif "афиша" in text:

        res = get_kharkiv_events()

        safe_send_message(
            message.chat.id,
            res
        )


# ============================================================
# 11. ЗАПУСК БОТА
# ============================================================

if __name__ == "__main__":

    print("========================================")
    print("      ХАРЬКОВ ИНФОРМЕР ЗАПУЩЕН")
    print("========================================")
    print("Погода запрашивается ТОЛЬКО")
    print("при нажатии кнопки '🌤 Погода'")
    print("Автообновления погоды отключены.")
    print("========================================")

    while True:

        try:

            bot.polling(
                none_stop=True,
                interval=2,
                timeout=15
            )

        except Exception as e:

            print(
                f"[TELEGRAM] Ошибка соединения: {e}"
            )

            print(
                "[TELEGRAM] Перезапуск через 3 секунды..."
            )

            time.sleep(3)
