import os

import sys

from pathlib import Path

from urllib.parse import urlparse

from dotenv import load_dotenv

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo

from telegram.ext import Application, CommandHandler, ContextTypes, TypeHandler



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

    return os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")





def get_telegram_effective_base() -> str:

    """Базовый URL для кнопок бота (HTTPS-туннель). Если не задан — PUBLIC_BASE_URL."""

    override = (os.environ.get("TELEGRAM_PUBLIC_BASE_URL") or "").strip().rstrip("/")

    if override:

        try:

            host = (urlparse(override).hostname or "").lower()

            # Служебные хосты бывших quick-tunnel логов — не использовать как публичный URL.

            if host in ("api.trycloudflare.com", "www.trycloudflare.com"):

                override = ""

        except Exception:

            pass

    if override:

        return override

    return get_public_base_url()





def _is_https(url: str) -> bool:

    try:

        return urlparse(url).scheme.lower() == "https"

    except Exception:

        return False





def get_website_url() -> str:

    eff = get_telegram_effective_base()

    raw = (os.environ.get("WEBSITE_URL") or "").strip().rstrip("/")

    url = raw if raw else eff

    # Кнопка «Сайт» — корень веб-версии (/), не миниапп (/miniapp/)

    if "/miniapp" in url.lower():

        url = eff

    return url.rstrip("/")





async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:

        return

    load_dotenv(ROOT / ".env", override=True)

    tg_base = get_telegram_effective_base()

    web_app_url = f"{tg_base}/miniapp/"

    website_url = get_website_url()

    if website_url == tg_base:

        website_url = f"{website_url}/"

    site_label = (os.environ.get("WEBSITE_BUTTON_LABEL") or "Сайт").strip() or "Сайт"

    mini_label = (os.environ.get("MINIAPP_BUTTON_LABEL") or "Мини-приложение").strip() or "Мини-приложение"



    intro = (

        "Привет! Это <b>VibeWork</b> — помощник в поиске своего пути и работы.\n\n"

        "Можно пройти короткий разбор про себя, посмотреть направления и вакансии ближе к твоему профилю.\n\n"

        "• Первая кнопка — <b>сайт</b> в браузере.\n"

        "• Вторая — <b>мини-приложение</b> в Telegram.\n\n"

        "Удачного старта!"

    )



    if _is_https(tg_base):

        keyboard = [

            [InlineKeyboardButton(site_label, url=website_url)],

            [InlineKeyboardButton(mini_label, web_app=WebAppInfo(url=web_app_url))],

        ]

        text = intro

    else:

        keyboard = [

            [InlineKeyboardButton(site_label, url=website_url)],

            [InlineKeyboardButton(mini_label, url=web_app_url)],

        ]

        text = (

            intro

            + "\n\n"

            + "<i>Нет HTTPS для Web App: укажите в <code>.env</code> прод-домен или другой HTTPS в "

            "<code>TELEGRAM_PUBLIC_BASE_URL</code>, перезапустите бота и снова нажмите /start.</i>"

        )



    await update.message.reply_text(

        text,

        reply_markup=InlineKeyboardMarkup(keyboard),

        parse_mode="HTML",

    )





def main():

    load_dotenv(ROOT / ".env", override=True)

    launch("Telegram-бота", subtitle=f"long polling · проект: {ROOT}")

    token = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()

    if not token:

        fail(

            "Запуск бота отменён",

            "в .env нет TELEGRAM_BOT_TOKEN",

            hint=f"Файл: {ROOT / '.env'} · см. docs/ENV.md · токен: @BotFather",

        )

        sys.exit(1)



    app = Application.builder().token(token).build()

    async def _reload_env_on_update(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:

        load_dotenv(ROOT / ".env", override=True)

    # Раньше команд: туннель дописывает .env после старта — без этого первый /start видит старый URL.
    app.add_handler(TypeHandler(Update, _reload_env_on_update), group=-1)

    app.add_handler(CommandHandler("start", start))



    pub = get_public_base_url()

    tg_base = get_telegram_effective_base()

    website = get_website_url()

    ok(

        "Бот запущен",

        Режим="Telegram long polling",

        **{"PUBLIC_BASE_URL": pub},

        **{"Telegram (кнопки)": tg_base},

        **{"Миниапп URL": f"{tg_base}/miniapp/"},

        **{"Сайт (кнопка)": website},

        **{"Web App": "да" if _is_https(tg_base) else "нет (нужен HTTPS в TELEGRAM_PUBLIC_BASE_URL или PUBLIC_BASE_URL)"},

        **{"Токен": mask_secret(token)},

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

