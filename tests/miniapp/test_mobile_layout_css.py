"""Статические проверки мобильной вёрстки мини-аппа (flex + radio/checkbox)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MINIAPP_HTML = ROOT / "miniapp" / "frontend" / "index.html"
SHELL_CSS = ROOT / "website" / "frontend" / "miniapp-shell.css"


def test_miniapp_excludes_radio_checkbox_from_global_input_width():
    text = MINIAPP_HTML.read_text(encoding="utf-8")
    assert ':not([type="checkbox"]):not([type="radio"])' in text
    assert ".radio-opt span" in text
    assert "min-width: 0" in text
    assert "flex: 1 1 0" in text


def test_miniapp_auth_agree_uses_single_label():
    text = MINIAPP_HTML.read_text(encoding="utf-8")
    assert 'class="auth-hh-agree"' in text
    assert "auth-hh-agree-text" in text
    assert '-webkit-appearance: checkbox' in text


def test_miniapp_shell_flex_option_rules():
    text = SHELL_CSS.read_text(encoding="utf-8")
    assert "#app .radio-opt span" in text
    assert "min-width: 0" in text
    assert "label:not(.radio-opt):not(.auth-hh-agree)" in text
    assert "#app .quiz-opt" in text


def test_reset_password_miniapp_back_link():
    text = (ROOT / "miniapp" / "frontend" / "reset-password.html").read_text(encoding="utf-8")
    assert "isMiniappContext" in text
    assert "/miniapp/?auth=login" in text


def test_miniapp_analysis_nested_spoilers():
    html = MINIAPP_HTML.read_text(encoding="utf-8")
    assert "analysisBlock" in html
    assert "shouldWrapAnalysisSpoiler" in html
    assert "analysis-block--plain" in html
    assert "analysis-spoiler--nested" in html
    assert "analysis-spoiler--root" in html
    assert "renderAdvicePlanSectionHtml" in html
    assert "renderLearnResourceSpoiler" in html


def test_miniapp_role_confirmation_ui():
    html = MINIAPP_HTML.read_text(encoding="utf-8")
    assert "buildRoleConfirmationHtml" in html
    assert "role/accept" in html
    assert "role/reject" in html
    assert "roleAcceptBtn" in html
    assert "Подходит" in html
    assert "Не подходит" in html
    assert "Подобрать другое" in html


def test_miniapp_path_tab_split():
    html = MINIAPP_HTML.read_text(encoding="utf-8")
    assert '{ id: \'analysis\', label: \'Путь\'' in html
    assert "buildPathStepsActionHtml" in html
    assert "buildPathAnalysisMetricsHtml" in html
    assert "buildPathSubtabBar" in html
    assert "Шаги действия" in html
    assert "syncPathSubTabForPayload" in html
    assert "mountPathTabContent" in html


def test_miniapp_anydo_learning_path_ui():
    html = MINIAPP_HTML.read_text(encoding="utf-8")
    assert "renderLearningPathAnyDo" in html
    assert "wirePathStepsActions" in html
    assert "postLearningStepStatus" in html
    assert "/vibework/learning/progress/" in html
    assert "anydo-path" in html
    assert "anydo-step__check" in html
    assert "Следующий этап" in html


def test_miniapp_radar_chart_colored_nodes_and_legend_dots():
    html = MINIAPP_HTML.read_text(encoding="utf-8")
    assert "RADAR_AXIS_COLORS" in html
    assert "radar-chip-dot" in html
    assert "radarAxisColor" in html
    assert "radar-spoke" in html
    assert "radar-axis-label" not in html


def test_miniapp_resolves_test_sphere_from_profile_and_web_interest():
    html = MINIAPP_HTML.read_text(encoding="utf-8")
    for name in (
        "resolveTestSphereId",
        "webInterestToSphereId",
        "sphereIdToWebInterest",
        "applyTestSphereSelectValue",
        "sphere_to_web_interest",
    ):
        assert name in html


def test_miniapp_keyboard_hides_menu_on_mobile():
    html = MINIAPP_HTML.read_text(encoding="utf-8")
    css = SHELL_CSS.read_text(encoding="utf-8")
    assert "initMobileKeyboardMenuHide" in html
    assert "data-vw-keyboard-open" in html
    assert "data-vw-keyboard-open" in css
    assert ".bottom-nav" in css
    assert "__vwResetKeyboardChrome" in html
    assert "renderShell" in html
    assert "__vwResetKeyboardChrome" in html.split("async function renderShell")[1][:800]
