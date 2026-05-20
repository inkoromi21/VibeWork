/**
 * Общая UI-логика VibeWork: анкета, тест, онбординг (сайт + миниапп).
 */
(function (global) {
    'use strict';

    var NEW_ACCOUNT_FLAG = 'vibework_new_account';

    function courseGradeOptionsForEducation(eduDetail) {
        var d = String(eduDetail || '').trim();
        if (d === 'school_8_11') {
            return [
                { v: '8 класс', l: '8 класс' },
                { v: '9 класс', l: '9 класс' },
                { v: '10 класс', l: '10 класс' },
                { v: '11 класс', l: '11 класс' },
            ];
        }
        if (d === 'spo') {
            return [1, 2, 3, 4].map(function (n) {
                return { v: n + ' курс', l: n + ' курс' };
            });
        }
        if (d === 'univ_bachelor' || d === 'univ_master') {
            return [1, 2, 3, 4, 5, 6].map(function (n) {
                return { v: n + ' курс', l: n + ' курс' };
            });
        }
        if (d === 'graduate') {
            return [{ v: 'выпускник', l: 'Выпускник' }];
        }
        return null;
    }

    function findFieldEl(root, fieldId) {
        if (!root) return null;
        return (
            root.querySelector('[data-fid="' + fieldId + '"]') ||
            root.querySelector('[data-sheet-field="' + fieldId + '"]')
        );
    }

    /**
     * @param {HTMLElement} root
     * @param {{ esc?: function, onChange?: function }} hooks
     */
    function syncCourseGradeField(root, hooks) {
        hooks = hooks || {};
        var esc = hooks.esc || function (s) {
            return String(s)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;');
        };
        var edu = findFieldEl(root, 'education_detail');
        var cg = findFieldEl(root, 'course_grade');
        if (!edu || !cg) return;
        var opts = courseGradeOptionsForEducation(edu.value);
        var prev = String(cg.value || '').trim();
        var parent = cg.parentNode;
        if (!parent) return;

        if (!opts) {
            if (cg.tagName !== 'INPUT') {
                var inp = document.createElement('input');
                inp.type = 'text';
                inp.setAttribute('data-fid', 'course_grade');
                inp.setAttribute('data-sheet-field', 'course_grade');
                inp.placeholder = '10 класс, 2 курс…';
                inp.className = cg.className || '';
                inp.value = prev;
                parent.replaceChild(inp, cg);
                inp.addEventListener('input', function () {
                    if (hooks.onChange) hooks.onChange(inp.value);
                });
            }
            return;
        }

        var sel = cg;
        if (cg.tagName !== 'SELECT') {
            sel = document.createElement('select');
            sel.setAttribute('data-fid', 'course_grade');
            sel.setAttribute('data-sheet-field', 'course_grade');
            sel.className = cg.className || '';
            parent.replaceChild(sel, cg);
        }
        sel.innerHTML =
            '<option value="">— выберите —</option>' +
            opts
                .map(function (o) {
                    return (
                        '<option value="' +
                        esc(o.v) +
                        '">' +
                        esc(o.l) +
                        '</option>'
                    );
                })
                .join('');
        if (prev) {
            var optsList = sel.options;
            for (var i = 0; i < optsList.length; i++) {
                if (optsList[i].value === prev) {
                    sel.value = prev;
                    break;
                }
            }
        }
        if (!sel.dataset.vwCourseGradeBound) {
            sel.dataset.vwCourseGradeBound = '1';
            sel.addEventListener('change', function () {
                if (hooks.onChange) hooks.onChange(sel.value);
            });
        }
    }

    function wireEducationDetailForCourseGrade(root, hooks) {
        var edu = findFieldEl(root, 'education_detail');
        if (!edu || edu.dataset.vwEduGradeBound) return;
        edu.dataset.vwEduGradeBound = '1';
        edu.addEventListener('change', function () {
            if (hooks.onEducationChange) hooks.onEducationChange(edu.value);
            syncCourseGradeField(root, hooks);
        });
    }

    /**
     * @param {object} schema
     * @param {object} profile
     * @param {function} esc
     * @param {{ profileFieldDisplay: function, sectionTitle?: function, skipSections?: object }} helpers
     */
    function buildProfileSummaryHtml(schema, profile, esc, helpers) {
        helpers = helpers || {};
        var profileFieldDisplay = helpers.profileFieldDisplay;
        var sectionTitle =
            helpers.sectionTitle ||
            function (sec) {
                return sec.title || '';
            };
        var skipSections = helpers.skipSections || { skills_soft: true };
        if (!profileFieldDisplay) return '<p class="muted">Нет данных.</p>';

        var blocks = [];
        var sections = (schema && schema.sections) || [];
        for (var si = 0; si < sections.length; si++) {
            var sec = sections[si];
            if (skipSections[sec.id]) continue;
            var fields = sec.fields || [];
            var itemsHtml = '';
            for (var fi = 0; fi < fields.length; fi++) {
                var f = fields[fi];
                var disp = profileFieldDisplay(schema, profile, f);
                if (!disp) continue;
                var wide = f.type === 'textarea' ? ' profile-complete-item--wide' : '';
                var valueHtml = '';
                if (disp.chips && disp.chips.length) {
                    valueHtml =
                        '<span class="profile-complete-chips">' +
                        disp.chips
                            .map(function (c) {
                                return (
                                    '<span class="profile-complete-chip">' +
                                    esc(c) +
                                    '</span>'
                                );
                            })
                            .join('') +
                        '</span>';
                } else {
                    valueHtml = esc(disp.text || '—');
                }
                itemsHtml +=
                    '<div class="profile-complete-item' +
                    wide +
                    '"><span class="profile-complete-label">' +
                    esc(f.label || f.id) +
                    '</span><span class="profile-complete-value">' +
                    valueHtml +
                    '</span></div>';
            }
            if (!itemsHtml) continue;
            blocks.push(
                '<section class="profile-complete-block"><h3 class="profile-complete-block-title">' +
                esc(sectionTitle(sec)) +
                '</h3><div class="profile-complete-grid">' +
                itemsHtml +
                '</div></section>'
            );
        }
        return blocks.length
            ? blocks.join('')
            : '<p class="muted">Нет сохранённых ответов.</p>';
    }

    function isNewAccountOnboarding() {
        try {
            if (localStorage.getItem(NEW_ACCOUNT_FLAG) === '1') return true;
            return new URLSearchParams(window.location.search).get('onboarding') === '1';
        } catch (e) {
            return false;
        }
    }

    function setNewAccountOnboardingFlag() {
        try {
            localStorage.setItem(NEW_ACCOUNT_FLAG, '1');
        } catch (e) {}
    }

    function clearNewAccountOnboardingFlag() {
        try {
            localStorage.removeItem(NEW_ACCOUNT_FLAG);
            var u = new URL(window.location.href);
            if (u.searchParams.has('onboarding')) {
                u.searchParams.delete('onboarding');
                window.history.replaceState({}, '', u.pathname + u.search + u.hash);
            }
        } catch (e) {}
    }

    global.VibeWorkShared = {
        NEW_ACCOUNT_FLAG: NEW_ACCOUNT_FLAG,
        courseGradeOptionsForEducation: courseGradeOptionsForEducation,
        syncCourseGradeField: syncCourseGradeField,
        wireEducationDetailForCourseGrade: wireEducationDetailForCourseGrade,
        buildProfileSummaryHtml: buildProfileSummaryHtml,
        isNewAccountOnboarding: isNewAccountOnboarding,
        setNewAccountOnboardingFlag: setNewAccountOnboardingFlag,
        clearNewAccountOnboardingFlag: clearNewAccountOnboardingFlag,
    };
})(typeof window !== 'undefined' ? window : this);
