"""Нормализация пароля из формы / JSON (Telegram WebView, вставка из буфера)."""


def sanitize_password_input(raw: object) -> str:
    """
    Убирает то, что часто ломает проверку bcrypt при том же пароле в браузере:
    \\r, zero-width, пробельные символы только по краям (не трогаем пробел внутри).
    """
    if raw is None:
        return ""
    s = str(raw).replace("\r", "")
    for z in ("\u200b", "\u200c", "\u200d", "\ufeff"):
        s = s.replace(z, "")
    return s.strip(" \t\n\v\f")
