import threading
import time
import os

from flask import Flask
import requests
import telebot
from telebot import types


# ============================================================
# FLASK ДЛЯ RENDER
# ============================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Bot is running!"


def run_flask():
    app.run(host="0.0.0.0", port=8080)


threading.Thread(target=run_flask, daemon=True).start()


# ============================================================
# TELEGRAM
# ============================================================

# Токен берём из Render -> Environment -> BOT_TOKEN
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError(
        "Не найден BOT_TOKEN. "
        "Добавь BOT_TOKEN в Environment Variables на Render."
    )

bot = telebot.TeleBot(BOT_TOKEN)


# ============================================================
# БЕЗОПАСНАЯ ОТПРАВКА СООБЩЕНИЯ
# ============================================================

def safe_send_message(chat_id, text, reply_markup=None):

    for attempt in range(3):

        try:

            bot.send_message(
                chat_id,
                text,
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=reply_markup
            )

            return

        except Exception as e:

            print(
                f"Ошибка отправки "
                f"(попытка {attempt + 1}/3): {e}"
            )

            time.sleep(2)


# ============================================================
# ПАРТНЁР
# ============================================================

PARTNER_FOOTER = (
    "\n\n"
    "— — — — — — — — — —\n"
    "📢 <b>Наш партнёр:</b> "
    '<a href="https://t.me/kuplyu_prodam_kh">'
    "Куплю Продам"
    "</a>"
)


# ============================================================
# 1. ПОГОДА
# ============================================================

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
                "https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}"
                "&current=temperature_2m,"
                "wind_speed_10m,weather_code"
                "&timezone=auto"
            )

            res = requests.get(
                url,
                timeout=10
            )

            res.raise_for_status()

            data = res.json()

            curr = data.get("current", {})

            temp_value = curr.get("temperature_2m")
            wind_value = curr.get("wind_speed_10m")
            code_value = curr.get("weather_code")

            if (
                temp_value is None
                or wind_value is None
                or code_value is None
            ):
                raise ValueError(
                    f"Нет необходимых данных: {curr}"
                )

            temp = round(float(temp_value))
            wind = round(float(wind_value))
            code = int(code_value)

            temps.append(temp)
            winds.append(wind)

            if code in [
                51, 53, 55,
                56, 57,
                61, 63, 65,
                66, 67,
                80, 81, 82,
                95, 96, 99
            ]:

                rain_expected = True

            response_text += (
                f"📍 <b>{city}</b>\n"
                f"• Температура: {temp}°C\n"
                f"• Ветер: {wind} км/ч\n\n"
            )

        except Exception as e:

            print(
                f"Ошибка загрузки погоды "
                f"({city}): {e}"
            )

            response_text += (
                f"📍 <b>{city}</b>\n"
                f"• ⚠️ Не удалось получить данные\n\n"
            )

    # --------------------------------------------------------
    # СОВЕТ ПО ОДЕЖДЕ
    # --------------------------------------------------------

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

            advice.append(
                "💨 Сильный ветер."
            )

        if rain_expected:

            advice.append(
                "☔ Возможны осадки — "
                "лучше взять зонт."
            )

        response_text += (
            "💡 <b>Совет по одежде:</b> "
            + " ".join(advice)
        )

    else:

        response_text += (
            "⚠️ <b>Не удалось получить данные "
            "о погоде.</b>"
        )

    return response_text + PARTNER_FOOTER


# ============================================================
# 2. КУРСЫ ВАЛЮТ И КРИПТОВАЛЮТ
# ============================================================

def get_currency_rates():

    text = (
        "💵 <b>КУРСЫ ВАЛЮТ И КРИПТОВАЛЮТ</b>\n\n"
    )

    # --------------------------------------------------------
    # USD — ПриватБанк
    # --------------------------------------------------------

    try:

        res = requests.get(
            "https://api.privatbank.ua/"
            "p24api/pubinfo?json&exchange&coursid=5",
            timeout=5
        ).json()

        for item in res:

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
            f"Ошибка USD: {e}"
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
            "https://bank.gov.ua/"
            "NBUStatService/v1/statdirectory/"
            "exchange?valcode=EUR&json",
            timeout=5
        ).json()

        if res_eur:

            eur_rate = round(
                float(res_eur[0].get("rate")),
                2
            )

            text += (
                f"🇪🇺 <b>EUR/UAH:</b> "
                f"1 EUR = {eur_rate} грн (НБУ)\n"
            )

    except Exception as e:

        print(
            f"Ошибка EUR: {e}"
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
            "https://bank.gov.ua/"
            "NBUStatService/v1/statdirectory/"
            "exchange?valcode=PLN&json",
            timeout=5
        ).json()

        if res_pln:

            pln_rate = round(
                float(res_pln[0].get("rate")),
                2
            )

            text += (
                f"🇵🇱 <b>PLN/UAH:</b> "
                f"1 PLN = {pln_rate} грн (НБУ)\n"
            )

    except Exception as e:

        print(
            f"Ошибка PLN: {e}"
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
            "https://bank.gov.ua/"
            "NBUStatService/v1/statdirectory/"
            "exchange?valcode=CNY&json",
            timeout=5
        ).json()

        if res_cny:

            cny_rate = round(
                float(res_cny[0].get("rate")),
                2
            )

            text += (
                f"🇨🇳 <b>CNY/UAH:</b> "
                f"1 CNY = {cny_rate} грн (НБУ)\n"
            )

    except Exception as e:

        print(
            f"Ошибка CNY: {e}"
        )

        text += (
            "🇨🇳 <b>CNY/UAH:</b> "
            "Ошибка загрузки\n"
        )

    # --------------------------------------------------------
    # КРИПТОВАЛЮТЫ
    # --------------------------------------------------------

    text += (
        "\n🪙 <b>Криптовалюты (USD):</b>\n"
    )

    btc_price = 0.0
    eth_price = 0.0
    sol_price = 0.0
    xrp_price = 0.0

    try:

        req_btc = requests.get(
            "https://api.bybit.com/"
            "v5/market/tickers?"
            "category=spot&symbol=BTCUSDT",
            timeout=3
        ).json()

        req_eth = requests.get(
            "https://api.bybit.com/"
            "v5/market/tickers?"
            "category=spot&symbol=ETHUSDT",
            timeout=3
        ).json()

        req_sol = requests.get(
            "https://api.bybit.com/"
            "v5/market/tickers?"
            "category=spot&symbol=SOLUSDT",
            timeout=3
        ).json()

        req_xrp = requests.get(
            "https://api.bybit.com/"
            "v5/market/tickers?"
            "category=spot&symbol=XRPUSDT",
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
            f"Ошибка Bybit: {e}"
        )

        # ----------------------------------------------------
        # РЕЗЕРВ MEXC
        # ----------------------------------------------------

        try:

            req_btc = requests.get(
                "https://api.mexc.com/"
                "api/v3/ticker/price?symbol=BTCUSDT",
                timeout=3
            ).json()

            req_eth = requests.get(
                "https://api.mexc.com/"
                "api/v3/ticker/price?symbol=ETHUSDT",
                timeout=3
            ).json()

            req_sol = requests.get(
                "https://api.mexc.com/"
                "api/v3/ticker/price?symbol=SOLUSDT",
                timeout=3
            ).json()

            req_xrp = requests.get(
                "https://api.mexc.com/"
                "api/v3/ticker/price?symbol=XRPUSDT",
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
                f"Ошибка MEXC: {e}"
            )

    if btc_price > 0:

        text += (
            f"• <b>BTC:</b> "
            f"${btc_price:,.2f}\n"
        )

        text += (
            f"• <b>ETH:</b> "
            f"${eth_price:,.2f}\n"
        )

        text += (
            f"• <b>SOL:</b> "
            f"${sol_price:,.2f}\n"
        )

        text += (
            f"• <b>XRP:</b> "
            f"${xrp_price:,.4f}\n"
        )

    else:

        text += (
            "• Не удалось загрузить "
            "курсы криптовалют\n"
        )

    return text + PARTNER_FOOTER


# ============================================================
# 3. РЕЛИГИЯ
# ============================================================

def get_religion_info():

    text = (
        "☦️ <b>РЕЛИГИЯ</b>\n\n"
        "📖 <b>Православные ресурсы:</b>\n\n"
        '• <a href="https://azbyka.ru/">'
        "Православный портал — Азбука</a>\n"
        '• <a href="https://church.ua/">'
        "Сайт УПЦ</a>\n"
        '• <a href="https://t.me/upc_news">'
        "Официальный Telegram УПЦ</a>\n\n"
        "💡 <i>Молитвы, Евангелие дня, "
        "церковный календарь и новости.</i>"
    )

    return text + PARTNER_FOOTER


# ============================================================
# 4. АФИША ХАРЬКОВА
# ============================================================

def get_kharkiv_events():

    text = (
        "🎭 <b>АФИША ХАРЬКОВ</b>\n\n"
    )

    text += (
        "🎟 <b>Спектакли, концерты, "
        "шоу и театры:</b>\n"
    )

    text += (
        '• <a href="https://kharkiv.internet-bilet.ua/">'
        "Internet-Bilet</a>\n"
    )

    text += (
        '• <a href="https://kharkiv.karabas.com/ru/">'
        "Karabas</a>\n\n"
    )

    text += (
        "🎬 <b>Кино:</b>\n"
    )

    text += (
        '• <a href="https://multiplex.ua/cinema/kharkiv/nikolsky">'
        "Multiplex — ТРЦ Никольский</a>\n\n"
    )

    text += (
        "💡 <i>Нажмите на ссылку, "
        "чтобы открыть расписание "
        "и купить билеты.</i>"
    )

    return text + PARTNER_FOOTER


# ============================================================
# 🏛 5. ГОСУСЛУГИ
# ============================================================

def send_gosuslugi(chat_id):

    keyboard = types.InlineKeyboardMarkup(
        row_width=1
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "📋 Запись в ЦНАП",
            url="https://dozvil.kh.ua/queue/form"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🏛 ЦНАП Харькова",
            url="https://dozvil.kh.ua/"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🏙 Харьковский горсовет",
            url="https://city.kharkiv.ua/"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🪪 ДМС — электронные услуги",
            url="https://dmsu.gov.ua/"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🛂 Паспортный сервис",
            url="https://kharkiv.pasport.org.ua/"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "⚖️ Минюст Харьковщины",
            url="https://kharkivjust.gov.ua/"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🏛 Харьковский облсовет",
            url="https://oblrada-kharkiv.gov.ua/"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🏢 Харьковская ОВА",
            url="https://kharkivoda.gov.ua/"
        )
    )

    text = (
        "🏛 <b>ГОСУСЛУГИ ХАРЬКОВА</b>\n\n"
        "📋 <b>Документы и административные услуги</b>\n"
        "ЦНАП, паспорта, городские и областные "
        "органы власти.\n\n"
        "Выберите нужный сервис:"
    )

    safe_send_message(
        chat_id,
        text,
        keyboard
    )


# ============================================================
# 🚇 6. ТРАНСПОРТ
# ============================================================

def send_transport(chat_id):

    keyboard = types.InlineKeyboardMarkup(
        row_width=1
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🗺 EasyWay — транспорт на карте",
            url="https://www.eway.in.ua/ua/cities/kharkiv"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🚇 Харьковский метрополитен",
            url="https://www.metro.kharkiv.ua/"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🎫 E-Ticket Харькова",
            url="https://eticket.kharkiv.ua/"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🚆 Укрзалізниця — билеты",
            url="https://booking.uz.gov.ua/"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🚆 Укрзалізниця — табло",
            url="https://booking.uz.gov.ua/"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🚌 Автобусные билеты",
            url="https://inbus.ua/"
        )
    )

    text = (
        "🚇 <b>ТРАНСПОРТ ХАРЬКОВА</b>\n\n"
        "🚌 <b>Городской транспорт</b>\n"
        "Карта маршрутов и движение транспорта.\n\n"
        "🚇 <b>Метро</b>\n"
        "Официальный сайт и информация "
        "Харьковского метрополитена.\n\n"
        "🚆 <b>Железная дорога</b>\n"
        "Билеты, табло и задержки поездов.\n\n"
        "🚌 <b>Автобусы</b>\n"
        "Поиск и покупка билетов.\n\n"
        "Выберите нужный сервис:"
    )

    safe_send_message(
        chat_id,
        text,
        keyboard
    )


# ============================================================
# 🏥 7. МЕДИЦИНА
# ============================================================

def send_medicine(chat_id):

    keyboard = types.InlineKeyboardMarkup(
        row_width=1
    )

    # 103
    keyboard.add(
        types.InlineKeyboardButton(
            "🚑 103 — скорая помощь",
            callback_data="medical_103"
        )
    )

    # 112
    keyboard.add(
        types.InlineKeyboardButton(
            "🆘 112 — экстренная помощь",
            callback_data="medical_112"
        )
    )

    # Медицинский портал Харькова
    keyboard.add(
        types.InlineKeyboardButton(
            "🏥 Медучреждения Харькова",
            url="https://medical.city.kharkiv.ua/"
        )
    )

    # Поиск лекарств
    keyboard.add(
        types.InlineKeyboardButton(
            "💊 Поиск лекарств и аптек",
            url="https://tabletki.ua/"
        )
    )

    # НСЗУ
    keyboard.add(
        types.InlineKeyboardButton(
            "🩺 НСЗУ — найти врача",
            url="https://nszu.gov.ua/"
        )
    )

    # МОЗ
    keyboard.add(
        types.InlineKeyboardButton(
            "📞 МОЗ Украины",
            url="https://moz.gov.ua/"
        )
    )

    text = (
        "🏥 <b>МЕДИЦИНА ХАРЬКОВА</b>\n\n"
        "🚑 <b>Экстренная помощь</b>\n"
        "103 — скорая медицинская помощь.\n"
        "112 — единый номер экстренной помощи.\n\n"
        "💊 <b>Аптеки и лекарства</b>\n"
        "Поиск препаратов и аптек.\n\n"
        "🏥 <b>Медучреждения</b>\n"
        "Официальный медицинский портал Харькова.\n\n"
        "Выберите нужный сервис:"
    )

    safe_send_message(
        chat_id,
        text,
        keyboard
    )


# ============================================================
# 🏠 8. ЖКХ
# ============================================================

def send_zhkh(chat_id):

    keyboard = types.InlineKeyboardMarkup(
        row_width=1
    )

    # 1562
    keyboard.add(
        types.InlineKeyboardButton(
            "📞 1562 — диспетчерская",
            callback_data="zhkh_1562"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🏠 Портал 1562",
            url="https://1562.kharkov.ua/"
        )
    )

    # Электричество
    keyboard.add(
        types.InlineKeyboardButton(
            "⚡ Харьковоблэнерго",
            url="https://www.oblenergo.kharkiv.ua/"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "⚡ Контакты Харьковоблэнерго",
            callback_data="zhkh_energy"
        )
    )

    # Вода
    keyboard.add(
        types.InlineKeyboardButton(
            "💧 Харьковводоканал",
            url="https://vodokanal.kharkov.ua/"
        )
    )

    # Газ
    keyboard.add(
        types.InlineKeyboardButton(
            "🔥 Газ / Нафтогаз",
            url="https://gas.ua/"
        )
    )

    # Город
    keyboard.add(
        types.InlineKeyboardButton(
            "🏙 Харьковский горсовет",
            url="https://city.kharkiv.ua/"
        )
    )

    text = (
        "🏠 <b>ЖКХ ХАРЬКОВА</b>\n\n"
        "🚨 <b>Аварии и коммунальные проблемы</b>\n"
        "1562 — городская диспетчерская служба.\n\n"
        "⚡ <b>Электричество</b>\n"
        "Харьковоблэнерго.\n\n"
        "💧 <b>Вода</b>\n"
        "Харьковводоканал.\n\n"
        "🔥 <b>Газ</b>\n"
        "Газовые услуги и Нафтогаз.\n\n"
        "Выберите нужную службу:"
    )

    safe_send_message(
        chat_id,
        text,
        keyboard
    )


# ============================================================
# 📞 CALLBACK-КНОПКИ
# ============================================================

@bot.callback_query_handler(
    func=lambda call: call.data in [
        "medical_103",
        "medical_112",
        "zhkh_1562",
        "zhkh_energy"
    ]
)
def handle_service_callback(call):

    # --------------------------------------------------------
    # 103
    # --------------------------------------------------------

    if call.data == "medical_103":

        text = (
            "🚑 <b>СКОРАЯ ПОМОЩЬ</b>\n\n"
            "📞 <b>103</b>\n\n"
            "При необходимости экстренной "
            "медицинской помощи звоните 103."
        )

    # --------------------------------------------------------
    # 112
    # --------------------------------------------------------

    elif call.data == "medical_112":

        text = (
            "🆘 <b>ЕДИНЫЙ НОМЕР ЭКСТРЕННОЙ ПОМОЩИ</b>\n\n"
            "📞 <b>112</b>\n\n"
            "Единый номер экстренной помощи."
        )

    # --------------------------------------------------------
    # 1562
    # --------------------------------------------------------

    elif call.data == "zhkh_1562":

        text = (
            "📞 <b>ДИСПЕТЧЕРСКАЯ 1562</b>\n\n"
            "📞 <b>15-62</b>\n\n"
            "По вопросам коммунальных проблем:\n\n"
            "• 💧 вода\n"
            "• 🔥 отопление и газ\n"
            "• ⚡ электричество\n"
            "• 🛗 лифты\n"
            "• 🏠 содержание домов\n"
            "• 🚧 аварийные ситуации\n\n"
            "🌐 Заявку также можно подать "
            "через портал 1562."
        )

    # --------------------------------------------------------
    # Харьковоблэнерго
    # --------------------------------------------------------

    else:

        text = (
            "⚡ <b>ХАРЬКОВОБЛЭНЕРГО</b>\n\n"
            "Контакт-центр:\n\n"
            "📞 <b>0 800 508 413</b>\n"
            "📞 <b>050 05 40 413</b>\n"
            "📞 <b>067 23 40 413</b>\n"
            "📞 <b>063 05 40 413</b>\n\n"
            "Для актуальной информации "
            "об отключениях и других вопросах "
            "используйте официальный сайт."
        )

    bot.answer_callback_query(
        call.id
    )

    safe_send_message(
        call.message.chat.id,
        text
    )


# ============================================================
# 9. ГЛАВНОЕ МЕНЮ
# ============================================================

@bot.message_handler(
    commands=["start"]
)
def start(message):

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        row_width=2
    )

    # --------------------------------------------------------
    # РЯД 1
    # --------------------------------------------------------

    btn1 = types.KeyboardButton(
        "🌤 Погода"
    )

    btn2 = types.KeyboardButton(
        "💵 Курс валют"
    )

    # --------------------------------------------------------
    # РЯД 2
    # --------------------------------------------------------

    btn3 = types.KeyboardButton(
        "🚇 Транспорт"
    )

    btn4 = types.KeyboardButton(
        "🎭 Афиша Харьков"
    )

    # --------------------------------------------------------
    # РЯД 3
    # --------------------------------------------------------

    btn5 = types.KeyboardButton(
        "🏛 Госуслуги"
    )

    btn6 = types.KeyboardButton(
        "🏠 ЖКХ"
    )

    # --------------------------------------------------------
    # РЯД 4
    # --------------------------------------------------------

    btn7 = types.KeyboardButton(
        "🏥 Медицина"
    )

    btn8 = types.KeyboardButton(
        "☦️ Религия"
    )

    markup.add(
        btn1,
        btn2,
        btn3,
        btn4,
        btn5,
        btn6,
        btn7,
        btn8
    )

    bot.send_message(
        message.chat.id,
        "Приветствует Харьков Информер!",
        reply_markup=markup
    )


# ============================================================
# 10. ОБРАБОТКА КНОПОК
# ============================================================

@bot.message_handler(
    func=lambda message: True
)
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
            "[БОТ] Запрос погоды"
        )

        res = get_weather_with_advice()

        safe_send_message(
            message.chat.id,
            res
        )

    # --------------------------------------------------------
    # ВАЛЮТЫ
    # --------------------------------------------------------

    elif (
        "курс" in text
        or "валют" in text
    ):

        print(
            "[БОТ] Запрос курса валют"
        )

        res = get_currency_rates()

        safe_send_message(
            message.chat.id,
            res
        )

    # --------------------------------------------------------
    # ТРАНСПОРТ
    # --------------------------------------------------------

    elif "транспорт" in text:

        print(
            "[БОТ] Открыт раздел транспорта"
        )

        send_transport(
            message.chat.id
        )

    # --------------------------------------------------------
    # АФИША
    # --------------------------------------------------------

    elif "афиша" in text:

        print(
            "[БОТ] Открыта афиша"
        )

        res = get_kharkiv_events()

        safe_send_message(
            message.chat.id,
            res
        )

    # --------------------------------------------------------
    # ГОСУСЛУГИ
    # --------------------------------------------------------

    elif "госуслуги" in text:

        print(
            "[БОТ] Открыты госуслуги"
        )

        send_gosuslugi(
            message.chat.id
        )

    # --------------------------------------------------------
    # ЖКХ
    # --------------------------------------------------------

    elif "жкх" in text:

        print(
            "[БОТ] Открыт раздел ЖКХ"
        )

        send_zhkh(
            message.chat.id
        )

    # --------------------------------------------------------
    # МЕДИЦИНА
    # --------------------------------------------------------

    elif "медицина" in text:

        print(
            "[БОТ] Открыта медицина"
        )

        send_medicine(
            message.chat.id
        )

    # --------------------------------------------------------
    # РЕЛИГИЯ
    # --------------------------------------------------------

    elif "религия" in text:

        print(
            "[БОТ] Открыта религия"
        )

        res = get_religion_info()

        safe_send_message(
            message.chat.id,
            res
        )


# ============================================================
# 11. ЗАПУСК
# ============================================================

if __name__ == "__main__":

    print(
        "========================================"
    )

    print(
        "      ХАРЬКОВ ИНФОРМЕР ЗАПУЩЕН"
    )

    print(
        "========================================"
    )

    print(
        "🌤 Погода"
    )

    print(
        "💵 Курс валют"
    )

    print(
        "🚇 Транспорт"
    )

    print(
        "🎭 Афиша Харьков"
    )

    print(
        "🏛 Госуслуги"
    )

    print(
        "🏠 ЖКХ"
    )

    print(
        "🏥 Медицина"
    )

    print(
        "☦️ Религия"
    )

    print(
        "========================================"
    )

    while True:

        try:

            bot.polling(
                none_stop=True,
                interval=2,
                timeout=15
            )

        except Exception as e:

            print(
                f"Ошибка соединения: {e}"
            )

            print(
                "Перезапуск через 3 секунды..."
            )

            time.sleep(3)
