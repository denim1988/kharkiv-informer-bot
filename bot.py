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

BOT_TOKEN = os.getenv("BOT_TOKEN")

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
    """
    Получает текущую погоду через wttr.in.
    Запрос выполняется ТОЛЬКО при нажатии кнопки "🌤 Погода".
    Автоматического обновления нет.
    """

    response_text = "🌤 <b>ПОГОДА</b>\n\n"

    cities = {
        "Харьков": "Kharkiv",
        "Чугуев": "Chuhuiv",
        "Харьковская область": "Kharkiv"
    }

    temps = []
    winds = []
    rain_expected = False

    for city, location in cities.items():

        try:
            print(f"[ПОГОДА] Получаю данные: {city}")

            url = (
                f"https://wttr.in/{location}"
                "?format=j1"
                "&m"
                "&lang=ru"
            )

            headers = {
                "User-Agent": "KharkivInformerBot/1.0"
            }

            res = requests.get(
                url,
                headers=headers,
                timeout=15
            )

            print(
                f"[ПОГОДА] {city}: HTTP {res.status_code}"
            )

            res.raise_for_status()

            data = res.json()

            # Текущие условия
            current = data.get("current_condition")

            if not current:
                raise ValueError(
                    "В ответе отсутствует current_condition"
                )

            current = current[0]

            # Температура
            temp = int(
                float(current.get("temp_C"))
            )

            # Ощущается
            feels_like = int(
                float(current.get("FeelsLikeC"))
            )

            # Ветер
            wind = int(
                float(current.get("windspeedKmph"))
            )

            # Влажность
            humidity = int(
                float(current.get("humidity"))
            )

            # Давление
            pressure = current.get("pressure")

            # Облачность
            cloud = current.get("cloudcover")

            # Описание
            weather_desc = current.get(
                "lang_ru",
                current.get("weatherDesc", [])
            )

            if weather_desc:
                description = weather_desc[0].get(
                    "value",
                    ""
                )
            else:
                description = ""

            # Осадки
            precip = float(
                current.get("precipMM", 0)
            )

            if precip > 0:
                rain_expected = True

            temps.append(temp)
            winds.append(wind)

            # Emoji состояния погоды
            if precip > 0:
                weather_icon = "🌧️"
            elif cloud is not None and int(cloud) >= 70:
                weather_icon = "☁️"
            elif cloud is not None and int(cloud) >= 30:
                weather_icon = "🌤️"
            else:
                weather_icon = "☀️"

            response_text += (
                f"📍 <b>{city}</b>\n"
                f"{weather_icon} {description}\n"
                f"• 🌡 Температура: <b>{temp}°C</b>\n"
                f"• 🤔 Ощущается: {feels_like}°C\n"
                f"• 💨 Ветер: {wind} км/ч\n"
                f"• 💧 Влажность: {humidity}%\n"
                f"• 🌧 Осадки: {precip} мм\n"
                f"• ☁️ Облачность: {cloud}%\n"
                f"• 📊 Давление: {pressure} hPa\n\n"
            )

            print(
                f"[ПОГОДА] {city}: "
                f"{temp}°C, "
                f"ощущается {feels_like}°C, "
                f"ветер {wind} км/ч"
            )

        except Exception as e:

            print(
                f"[ОШИБКА ПОГОДЫ] {city}: {e}"
            )

            response_text += (
                f"📍 <b>{city}</b>\n"
                f"⚠️ Не удалось получить данные\n\n"
            )

    # ========================================================
    # СОВЕТ
    # ========================================================

    if temps:

        avg_temp = sum(temps) / len(temps)
        avg_wind = sum(winds) / len(winds)

        advice = []

        if avg_temp >= 25:

            advice.append(
                "🩳 Жарко — лёгкая летняя одежда."
            )

        elif avg_temp >= 22:

            advice.append(
                "👕 Тепло — футболка и лёгкие брюки/шорты."
            )

        elif avg_temp >= 15:

            advice.append(
                "🧥 Умеренно тепло — футболка + лёгкая кофта."
            )

        elif avg_temp >= 5:

            advice.append(
                "🧥 Прохладно — куртка или тёплая кофта."
            )

        else:

            advice.append(
                "🥶 Холодно — нужна тёплая одежда."
            )

        if avg_wind >= 20:

            advice.append(
                "💨 Сильный ветер — учитывай это при выходе."
            )

        elif avg_wind >= 12:

            advice.append(
                "💨 На улице ветрено."
            )

        if rain_expected:

            advice.append(
                "☔ Есть осадки — лучше взять зонт."
            )

        response_text += (
            "💡 <b>Совет:</b> "
            + " ".join(advice)
        )

    else:

        response_text += (
            "⚠️ <b>Не удалось получить данные "
            "о погоде.</b>"
        )

    print("[ПОГОДА] Запрос завершён.")

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
