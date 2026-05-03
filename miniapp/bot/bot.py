import os

import sys

from pathlib import Path



import requests

from dotenv import load_dotenv

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo

from telegram.ext import Application, CommandHandler, ContextTypes



_BOT_DIR = Path(__file__).resolve().parent

_MINIAPP_ROOT = _BOT_DIR.parent

ROOT = _MINIAPP_ROOT.parent

API_ROOT = _MINIAPP_ROOT / "backend"

sys.path.insert(0, str(_MINIAPP_ROOT))

sys.path.insert(0, str(API_ROOT))

os.chdir(ROOT)

load_dotenv(ROOT / ".env")



from terminal_theme import fail, launch, mask_secret, ok  # noqa: E402





def get_public_base_url() -> str:

    try:

        r = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=2)

        if r.status_code == 200:

            tunnels = r.json().get("tunnels") or []

            if tunnels:

                return tunnels[0].get("public_url", "").rstrip("/")

    except OSError:

        pass

    return os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")





def get_website_url() -> str:

    base = os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

    return (os.environ.get("WEBSITE_URL") or base).rstrip("/")





async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:

        return

    base = get_public_base_url()

    web_app_url = f"{base}/miniapp/"

    website_url = get_website_url()

    if website_url == base:

        website_url = f"{website_url}/"

    site_label = (os.environ.get("WEBSITE_BUTTON_LABEL") or "Временно недоступен").strip() or "Сайт"



    intro = (

        "Привет! Это <b>VibeWork</b> — помощник в поиске своего пути и работы.\n\n"

        "Можно пройти короткий разбор про себя, посмотреть направления и вакансии ближе к твоему профилю.\n\n"

        "• <b>Сайт</b> — полная веб-версия (сейчас <b>временно недоступна</b>). Кнопка со ссылкой и предупреждением ниже.\n"

        "• <b>Мини-приложение</b> — то же удобно прямо в Telegram (вторая кнопка).\n\n"

        "Удачного старта!"

    )



    if base.lower().startswith("https://"):

        keyboard = [

            [InlineKeyboardButton(site_label, url=website_url)],

            [InlineKeyboardButton("Открыть VibeWork", web_app=WebAppInfo(url=web_app_url))],

        ]

        text = intro

    else:

        keyboard = [

            [InlineKeyboardButton(site_label, url=website_url)],

            [InlineKeyboardButton("Мини-приложение в браузере", url=web_app_url)],

        ]

        text = (

            intro

            + "\n\n"

            + "<i>Чтобы мини-приложение открылось внутри Telegram как Web App, нужен HTTPS "

            "(ngrok на порт API или PUBLIC_BASE_URL=https://… в .env). "

            "Пока открой мини-приложение по ссылке в браузере — вторая кнопка.</i>"

        )



    await update.message.reply_text(

        text,

        reply_markup=InlineKeyboardMarkup(keyboard),

        parse_mode="HTML",

    )





def main():

    launch("Telegram-бота", subtitle=f"long polling · проект: {ROOT}")

    token = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()

    if not token:

        fail(

            "Запуск бота отменён",

            "в .env нет TELEGRAM_BOT_TOKEN",

            hint=f"Файл: {ROOT / '.env'} · шаблон: miniapp/.env.example · токен: @BotFather",

        )

        sys.exit(1)



    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))



    base = get_public_base_url()

    website = get_website_url()

    ngrok_ui = "http://127.0.0.1:4040 — HTTPS для Web App, если ngrok запущен"

    ok(

        "Бот запущен",

        Режим="Telegram long polling",

        **{"Публичный base (кнопки)": base},

        **{"Миниапп URL": f"{base}/miniapp/"},

        **{"Сайт (кнопка)": website},

        **{"Токен": mask_secret(token)},

        **{"ngrok UI": ngrok_ui},

    )



    try:

        app.run_polling()

    except KeyboardInterrupt:

        raise

    except Exception as e:

        fail("Ошибка запуска бота", str(e), hint="Сеть, Telegram API или неверный токен.")

        sys.exit(1)





if __name__ == "__main__":

    main()

