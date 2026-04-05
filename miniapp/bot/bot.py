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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    base = get_public_base_url()
    web_app_url = f"{base}/miniapp/"
    # Telegram accepts only https:// for WebApp buttons; http (e.g. localhost) must use a normal link.
    if base.lower().startswith("https://"):
        keyboard = [
            [InlineKeyboardButton("Открыть VibeWork", web_app=WebAppInfo(url=web_app_url))]
        ]
        text = "VibeWork — нажми кнопку:"
    else:
        keyboard = [[InlineKeyboardButton("Открыть в браузере", url=web_app_url)]]
        text = (
            "VibeWork — мини-приложение в Telegram требует HTTPS (запустите ngrok "
            "или задайте PUBLIC_BASE_URL=https://… в .env). "
            "Ниже — ссылка для браузера на этом компьютере (localhost)."
        )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


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
