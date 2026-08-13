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
    return "Харьков Информер работает!"


def run_flask():
    app.run(
        host="0.0.0.0",
        port=8080
    )


threading.Thread(
    target=run_flask,
    daemon=True
).start()


# ============================================================
# TELEGRAM
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError(
        "Не найден BOT_TOKEN. "
        "Добавь BOT_TOKEN в Render → Environment."
    )

bot = telebot.TeleBot(BOT_TOKEN)


# ============================================================
# ПАРТНЁРСКИЙ ПОДВАЛ
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
# БЕЗОПАСНАЯ ОТПРАВКА
# ============================================================

def safe_send_message(
    chat_id,
    text,
    reply_markup=None
):

    for attempt in range(3):

        try:

            bot.send_message(
                chat_id,
                text,
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=reply_markup
            )

            return True

        except Exception as e:

            print(
                f"Ошибка отправки "
                f"(попытка {attempt + 1}/3): {e}"
            )

            time.sleep(2)

    return False


# ============================================================
# 🌤 ПОГОДА
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
# 💵 КУРС ВАЛЮТ
# ============================================================

def get_currency_rates():

    text = (
        "💵 <b>КУРСЫ ВАЛЮТ "
        "И КРИПТОВАЛЮТ</b>\n\n"
    )

    # USD
    try:

        res = requests.get(
            "https://api.privatbank.ua/"
            "p24api/pubinfo?json&exchange&coursid=5",
            timeout=5
        ).json()

        for item in res:

            if item.get("ccy") == "USD":

                buy = round(
                    float(item["buy"]),
                    2
                )

                sale = round(
                    float(item["sale"]),
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

    # EUR
    try:

        data = requests.get(
            "https://bank.gov.ua/"
            "NBUStatService/v1/statdirectory/"
            "exchange?valcode=EUR&json",
            timeout=5
        ).json()

        if data:

            rate = round(
                float(data[0]["rate"]),
                2
            )

            text += (
                f"🇪🇺 <b>EUR/UAH:</b> "
                f"{rate} грн (НБУ)\n"
            )

    except Exception as e:

        print(
            f"Ошибка EUR: {e}"
        )

    # PLN
    try:

        data = requests.get(
            "https://bank.gov.ua/"
            "NBUStatService/v1/statdirectory/"
            "exchange?valcode=PLN&json",
            timeout=5
        ).json()

        if data:

            rate = round(
                float(data[0]["rate"]),
                2
            )

            text += (
                f"🇵🇱 <b>PLN/UAH:</b> "
                f"{rate} грн (НБУ)\n"
            )

    except Exception as e:

        print(
            f"Ошибка PLN: {e}"
        )

    # CNY
    try:

        data = requests.get(
            "https://bank.gov.ua/"
            "NBUStatService/v1/statdirectory/"
            "exchange?valcode=CNY&json",
            timeout=5
        ).json()

        if data:

            rate = round(
                float(data[0]["rate"]),
                2
            )

            text += (
                f"🇨🇳 <b>CNY/UAH:</b> "
                f"{rate} грн (НБУ)\n"
            )

    except Exception as e:

        print(
            f"Ошибка CNY: {e}"
        )

    # ========================================================
    # КРИПТА
    # ========================================================

    text += (
        "\n🪙 <b>Криптовалюты:</b>\n"
    )

    btc = 0
    eth = 0
    sol = 0
    xrp = 0

    try:

        symbols = [
            "BTCUSDT",
            "ETHUSDT",
            "SOLUSDT",
            "XRPUSDT"
        ]

        prices = {}

        for symbol in symbols:

            data = requests.get(
                "https://api.bybit.com/"
                "v5/market/tickers",
                params={
                    "category": "spot",
                    "symbol": symbol
                },
                timeout=5
            ).json()

            price = float(
                data["result"]["list"][0]["lastPrice"]
            )

            prices[symbol] = price

        btc = prices["BTCUSDT"]
        eth = prices["ETHUSDT"]
        sol = prices["SOLUSDT"]
        xrp = prices["XRPUSDT"]

    except Exception as e:

        print(
            f"Ошибка Bybit: {e}"
        )

        # Резерв MEXC
        try:

            for symbol, variable in [
                ("BTCUSDT", "btc"),
                ("ETHUSDT", "eth"),
                ("SOLUSDT", "sol"),
                ("XRPUSDT", "xrp")
            ]:

                data = requests.get(
                    "https://api.mexc.com/"
                    "api/v3/ticker/price",
                    params={
                        "symbol": symbol
                    },
                    timeout=5
                ).json()

                value = float(
                    data["price"]
                )

                if variable == "btc":
                    btc = value

                elif variable == "eth":
                    eth = value

                elif variable == "sol":
                    sol = value

                elif variable == "xrp":
                    xrp = value

        except Exception as mexc_error:

            print(
                f"Ошибка MEXC: "
                f"{mexc_error}"
            )

    if btc > 0:

        text += (
            f"• <b>BTC:</b> "
            f"${btc:,.2f}\n"
            f"• <b>ETH:</b> "
            f"${eth:,.2f}\n"
            f"• <b>SOL:</b> "
            f"${sol:,.2f}\n"
            f"• <b>XRP:</b> "
            f"${xrp:,.4f}\n"
        )

    else:

        text += (
            "• Не удалось загрузить "
            "криптовалюты\n"
        )

    return text + PARTNER_FOOTER


# ============================================================
# ☦️ РЕЛИГИЯ
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
        "Telegram УПЦ</a>\n\n"
        "💡 <i>Молитвы, Евангелие дня, "
        "церковный календарь и новости.</i>"
    )

    return text + PARTNER_FOOTER


# ============================================================
# 🎭 АФИША
# ============================================================

def get_kharkiv_events():

    text = (
        "🎭 <b>АФИША ХАРЬКОВ</b>\n\n"
        "🎟 <b>Спектакли, концерты, "
        "шоу и театры:</b>\n\n"
        '• <a href="https://kharkiv.internet-bilet.ua/">'
        "Internet-Bilet</a>\n"
        '• <a href="https://kharkiv.karabas.com/ru/">'
        "Karabas</a>\n\n"
        "🎬 <b>Кино:</b>\n\n"
        '• <a href="https://multiplex.ua/cinema/kharkiv/nikolsky">'
        "Multiplex — Никольский</a>\n\n"
        "💡 <i>Откройте ссылку, "
        "чтобы посмотреть расписание.</i>"
    )

    return text + PARTNER_FOOTER


# ============================================================
# 🏛 ГОСУСЛУГИ
# ============================================================

def send_gosuslugi(chat_id):

    keyboard = types.InlineKeyboardMarkup(
        row_width=1
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "📋 Запись в ЦНАП",
            url="https://dozvil.kh.ua/"
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
            "🪪 ДМС — услуги",
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
            "⚖️ Минюст",
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
        "📋 <b>Документы и административные услуги</b>\n\n"
        "Здесь собраны основные городские "
        "и государственные сервисы Харькова.\n\n"
        "Выберите нужный сервис:"
    )

    safe_send_message(
        chat_id,
        text + PARTNER_FOOTER,
        keyboard
    )


# ============================================================
# 🚇 ТРАНСПОРТ
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
        "Информация Харьковского метрополитена.\n\n"
        "🚆 <b>Железная дорога</b>\n"
        "Билеты и информация о поездах.\n\n"
        "🚌 <b>Автобусы</b>\n"
        "Поиск и покупка билетов.\n\n"
        "Выберите нужный сервис:"
    )

    safe_send_message(
        chat_id,
        text + PARTNER_FOOTER,
        keyboard
    )


# ============================================================
# 🏥 МЕДИЦИНА
# ============================================================

def send_medicine(chat_id):

    keyboard = types.InlineKeyboardMarkup(
        row_width=1
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🚑 103 — скорая помощь",
            callback_data="medical_103"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🆘 112 — экстренная помощь",
            callback_data="medical_112"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🏥 Медучреждения Харькова",
            url="https://medical.city.kharkiv.ua/"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "💊 Поиск лекарств и аптек",
            url="https://tabletki.ua/"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🩺 НСЗУ — найти врача",
            url="https://nszu.gov.ua/"
        )
    )

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
        "Медицинские сервисы Харькова.\n\n"
        "Выберите нужный сервис:"
    )

    safe_send_message(
        chat_id,
        text + PARTNER_FOOTER,
        keyboard
    )


# ============================================================
# 🏠 ЖКХ
# ============================================================

def send_zhkh(chat_id):

    keyboard = types.InlineKeyboardMarkup(
        row_width=1
    )

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

    keyboard.add(
        types.InlineKeyboardButton(
            "⚡ Харьковоблэнерго",
            url="https://www.oblenergo.kharkiv.ua/"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "💧 Харьковводоканал",
            url="https://vodokanal.kharkov.ua/"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🔥 Газ / Нафтогаз",
            url="https://gas.ua/"
        )
    )

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
        "Газовые услуги.\n\n"
        "Выберите нужную службу:"
    )

    safe_send_message(
        chat_id,
        text + PARTNER_FOOTER,
        keyboard
    )


# ============================================================
# 📞 CALLBACK-КНОПКИ
# ============================================================

@bot.callback_query_handler(
    func=lambda call: call.data in [
        "medical_103",
        "medical_112",
        "zhkh_1562"
    ]
)
def handle_callback(call):

    if call.data == "medical_103":

        text = (
            "🚑 <b>СКОРАЯ ПОМОЩЬ</b>\n\n"
            "📞 <b>103</b>\n\n"
            "Экстренная медицинская помощь."
        )

    elif call.data == "medical_112":

        text = (
            "🆘 <b>ЕДИНЫЙ НОМЕР "
            "ЭКСТРЕННОЙ ПОМОЩИ</b>\n\n"
            "📞 <b>112</b>\n\n"
            "Единый номер экстренной помощи."
        )

    elif call.data == "zhkh_1562":

        text = (
            "📞 <b>ДИСПЕТЧЕРСКАЯ 1562</b>\n\n"
            "📞 <b>15-62</b>\n\n"
            "По вопросам коммунальных проблем:\n\n"
            "• 💧 вода\n"
            "• 🔥 отопление\n"
            "• ⚡ электричество\n"
            "• 🛗 лифты\n"
            "• 🏠 содержание домов\n"
            "• 🚧 аварийные ситуации\n\n"
            "🌐 Заявку также можно подать "
            "через портал 1562."
        )

    else:

        text = (
            "⚠️ Информация временно недоступна."
        )

    bot.answer_callback_query(
        call.id
    )

    safe_send_message(
        call.message.chat.id,
        text + PARTNER_FOOTER
    )


# ============================================================
# 🚀 /START
# ============================================================

@bot.message_handler(
    commands=["start"]
)
def start(message):

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        row_width=2
    )

    markup.add(
        types.KeyboardButton(
            "🌤 Погода"
        ),
        types.KeyboardButton(
            "💵 Курс валют"
        ),
        types.KeyboardButton(
            "🚇 Транспорт"
        ),
        types.KeyboardButton(
            "🎭 Афиша Харьков"
        ),
        types.KeyboardButton(
            "🏛 Госуслуги"
        ),
        types.KeyboardButton(
            "🏠 ЖКХ"
        ),
        types.KeyboardButton(
            "🏥 Медицина"
        ),
        types.KeyboardButton(
            "☦️ Религия"
        )
    )

    bot.send_message(
        message.chat.id,
        "Приветствует Харьков Информер!",
        reply_markup=markup
    )


# ============================================================
# 🔘 ОБРАБОТКА КНОПОК
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
            "[БОТ] Нажата кнопка Погода"
        )

        result = (
            get_weather_with_advice()
        )

        safe_send_message(
            message.chat.id,
            result
        )

    # --------------------------------------------------------
    # КУРС ВАЛЮТ
    # --------------------------------------------------------

    elif (
        "курс" in text
        or "валют" in text
    ):

        print(
            "[БОТ] Нажата кнопка Курс валют"
        )

        result = (
            get_currency_rates()
        )

        safe_send_message(
            message.chat.id,
            result
        )

    # --------------------------------------------------------
    # ТРАНСПОРТ
    # --------------------------------------------------------

    elif "транспорт" in text:

        print(
            "[БОТ] Нажата кнопка Транспорт"
        )

        send_transport(
            message.chat.id
        )

    # --------------------------------------------------------
    # АФИША
    # --------------------------------------------------------

    elif "афиша" in text:

        print(
            "[БОТ] Нажата кнопка Афиша"
        )

        result = (
            get_kharkiv_events()
        )

        safe_send_message(
            message.chat.id,
            result
        )

    # --------------------------------------------------------
    # ГОСУСЛУГИ
    # --------------------------------------------------------

    elif "госуслуги" in text:

        print(
            "[БОТ] Нажата кнопка Госуслуги"
        )

        send_gosuslugi(
            message.chat.id
        )

    # --------------------------------------------------------
    # ЖКХ
    # --------------------------------------------------------

    elif "жкх" in text:

        print(
            "[БОТ] Нажата кнопка ЖКХ"
        )

        send_zhkh(
            message.chat.id
        )

    # --------------------------------------------------------
    # МЕДИЦИНА
    # --------------------------------------------------------

    elif "медицина" in text:

        print(
            "[БОТ] Нажата кнопка Медицина"
        )

        send_medicine(
            message.chat.id
        )

    # --------------------------------------------------------
    # РЕЛИГИЯ
    # --------------------------------------------------------

    elif "религия" in text:

        print(
            "[БОТ] Нажата кнопка Религия"
        )

        result = (
            get_religion_info()
        )

        safe_send_message(
            message.chat.id,
            result
        )


# ============================================================
# ▶️ ЗАПУСК
# ============================================================

if __name__ == "__main__":

    print(
        "================================"
    )

    print(
        "    ХАРЬКОВ ИНФОРМЕР ЗАПУЩЕН"
    )

    print(
        "================================"
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
        "================================"
    )

    while True:

        try:

            bot.polling(
                none_stop=True,
                interval=2,
                timeout=20
            )

        except Exception as e:

            print(
                f"Ошибка Telegram: {e}"
            )

            print(
                "Перезапуск через 5 секунд..."
            )

            time.sleep(5)
