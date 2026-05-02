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
sys.path.insert(0, str(API_ROOT))
os.chdir(ROOT)
load_dotenv(ROOT / ".env")


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
    # В текущем стеке сайт может обслуживаться тем же backend на корне (/).
    # Если WEBSITE_URL не задан, используем PUBLIC_BASE_URL.
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
    site_label = (os.environ.get("WEBSITE_BUTTON_LABEL") or "Сайт CareerCompass").strip() or "Сайт"

    intro = (
        "Привет! Это <b>VibeWork</b> — помощник в поиске своего пути и работы.\n\n"
        "Можно пройти короткий разбор про себя, посмотреть направления и вакансии ближе к твоему профилю.\n\n"
        "• <b>Сайт</b> — полная веб-версия (CareerCompass): диагностика, план, симулятор дня. Кнопка ниже.\n"
        "• <b>Мини-приложение</b> — то же удобно прямо в Telegram (вторая кнопка).\n\n"
        "Удачного старта!"
    )

    # Telegram accepts only https:// for WebApp buttons; http (e.g. localhost) must use a normal link.
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
    token = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        env_path = ROOT / ".env"
        print("Нужен TELEGRAM_BOT_TOKEN в .env в корне репозитория:")
        print(f"  {env_path}")
        print("Создайте файл: cp miniapp/.env.example .env  и вставьте токен от @BotFather.")
        sys.exit(1)
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    print("Бот запущен, base URL для кнопки:", get_public_base_url())
    app.run_polling()


if __name__ == "__main__":
    main()
