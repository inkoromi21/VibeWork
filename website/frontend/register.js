function showAuthGateError(msg) {
  const el = document.getElementById("auth-gate-error");
  if (!el) return;
  if (!msg) {
    el.textContent = "";
    el.classList.add("hidden");
    return;
  }
  el.textContent = msg;
  el.classList.remove("hidden");
}

async function redirectIfAuthenticated() {
  try {
    const r = await fetch("/api/auth/me", { credentials: "include" });
    const j = await r.json();
    if (j.authenticated) {
      window.location.replace("/");
    }
  } catch (_) {}
}

document.getElementById("btn-auth-register")?.addEventListener("click", async () => {
  showAuthGateError("");
  const email = document.getElementById("auth-email")?.value?.trim();
  const password = document.getElementById("auth-password")?.value || "";
  const agree = document.getElementById("hh-agree");
  if (!email || password.length < 8) {
    showAuthGateError("Укажите email и пароль не короче 8 символов.");
    return;
  }
  if (agree && !agree.checked) {
    showAuthGateError("Чтобы зарегистрироваться, подтвердите согласие с офертой.");
    return;
  }
  const btn = document.getElementById("btn-auth-register");
  if (btn) btn.disabled = true;
  try {
    const { ok, j } = await authRegisterEmail(email, password);
    if (!ok) {
      showAuthGateError(formatAuthError(j.detail) || "Регистрация не удалась");
      return;
    }
    const me = await fetch("/api/auth/me", { credentials: "include" }).then((r) => r.json());
    if (!me.authenticated) {
      showAuthGateError("Аккаунт создан. Войдите на главной странице.");
      window.setTimeout(() => {
        window.location.href = "/";
      }, 1500);
      return;
    }
    window.location.replace("/");
  } catch (e) {
    showAuthGateError(e.message || "Регистрация не удалась");
  } finally {
    if (btn) btn.disabled = false;
  }
});

redirectIfAuthenticated();
