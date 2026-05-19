/** Общая авторизация по email для сайта (вход на /, регистрация на /register). */
const ACCESS_TOKEN_KEY = "career_access_token";

function formatAuthError(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return (
      detail
        .map((x) => (x && typeof x.msg === "string" ? x.msg : ""))
        .filter(Boolean)
        .join(" ") || "Ошибка запроса"
    );
  }
  return "Ошибка запроса";
}

async function authRequestEmail(email, password) {
  const login = (email || "").trim();
  const r = await fetch("/auth/email/login", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: login, password }),
  });
  const j = await r.json().catch(() => ({}));
  if (r.ok && j.admin) {
    window.location.assign(j.redirect || "/admin");
    return { ok: true, j, admin: true };
  }
  if (r.ok && j.access_token) {
    try {
      localStorage.setItem(ACCESS_TOKEN_KEY, j.access_token);
      if (j.user_id) localStorage.setItem("userId", j.user_id);
      if (j.email) localStorage.setItem("userEmail", j.email);
    } catch (_) {}
    return { ok: true, j };
  }
  return { ok: r.ok, j };
}

async function authRegisterEmail(email, password) {
  const r = await fetch("/auth/email/register", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: (email || "").trim(), password }),
  });
  const j = await r.json().catch(() => ({}));
  if (r.ok && j.access_token) {
    try {
      localStorage.setItem(ACCESS_TOKEN_KEY, j.access_token);
      if (j.user_id) localStorage.setItem("userId", j.user_id);
      if (j.email) localStorage.setItem("userEmail", j.email);
    } catch (_) {}
    return { ok: true, j };
  }
  return { ok: r.ok, j };
}
