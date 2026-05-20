(function (global) {
  function setPasswordVisible(btn, inp, visible) {
    inp.type = visible ? "text" : "password";
    btn.setAttribute("aria-pressed", visible ? "true" : "false");
    btn.setAttribute("aria-label", visible ? "Скрыть пароль" : "Показать пароль");
    btn.classList.toggle("auth-pwd-toggle--visible", visible);
  }

  function wire(btn, inp) {
    if (!btn || !inp || btn.dataset.pwdToggleWired === "1") return;
    btn.dataset.pwdToggleWired = "1";
    btn.addEventListener("click", function () {
      setPasswordVisible(btn, inp, inp.type === "password");
    });
  }

  function initAll() {
    document.querySelectorAll(".auth-pwd-toggle[data-pwd-toggle-for]").forEach(function (btn) {
      var id = btn.getAttribute("data-pwd-toggle-for");
      if (!id) return;
      wire(btn, document.getElementById(id));
    });
  }

  global.wireAuthPasswordToggle = function (btnId, inpId) {
    wire(document.getElementById(btnId), document.getElementById(inpId));
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAll);
  } else {
    initAll();
  }
})(typeof window !== "undefined" ? window : globalThis);
