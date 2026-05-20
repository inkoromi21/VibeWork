/**
 * Общая UI-логика VibeWork: анкета, тест, онбординг (сайт + миниапп).
 */
(function (global) {
    'use strict';

    var NEW_ACCOUNT_FLAG = 'vibework_new_account';
    var PROFILE_DRAFT_LEGACY = 'vibework_profile_draft_v1';
    var PROFILE_DRAFT_PREFIX = 'vibework_profile_draft_v1_';
    var ACTIVE_USER_KEY = 'vibework_active_user_id';

    function profileDraftKey(userId) {
        if (!userId) return PROFILE_DRAFT_LEGACY;
        return PROFILE_DRAFT_PREFIX + String(userId);
    }

    function clearLegacyProfileDraft() {
        try {
            localStorage.removeItem(PROFILE_DRAFT_LEGACY);
        } catch (e) {}
    }

    function clearProfileDraftForUser(userId) {
        try {
            if (userId) localStorage.removeItem(profileDraftKey(userId));
            clearLegacyProfileDraft();
        } catch (e) {}
    }

    function rememberActiveUserId(userId) {
        try {
            if (userId) localStorage.setItem(ACTIVE_USER_KEY, String(userId));
            else localStorage.removeItem(ACTIVE_USER_KEY);
        } catch (e) {}
    }

    function readActiveUserId() {
        try {
            return localStorage.getItem(ACTIVE_USER_KEY) || '';
        } catch (e) {
            return '';
        }
    }

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
        if (opts.length === 1) {
            sel.value = opts[0].v;
            if (hooks.onChange) hooks.onChange(sel.value);
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

    function choiceLabelForQuestion(q, choice) {
        if (!q || choice == null || choice === '') return '—';
        var c = String(choice);
        var opts = q.options || [];
        for (var i = 0; i < opts.length; i++) {
            var o = opts[i];
            var id = o.id != null ? String(o.id) : o.k != null ? String(o.k) : '';
            if (id === c) {
                var lbl = o.label != null ? o.label : o.t != null ? o.t : '';
                return String(lbl || c);
            }
        }
        return c;
    }

    /**
     * @param {Array<{title?: string, questions: object[]}>} blocks
     * @param {object} answersMap question_id -> choice
     * @param {function} esc
     * @param {{ lead?: string }} opts
     */
    function buildQuizSummaryHtml(blocks, answersMap, esc, opts) {
        opts = opts || {};
        answersMap = answersMap || {};
        var lead = opts.lead || 'Ваши ответы по всем вопросам теста.';
        var sectionsHtml = '';
        var userNum = 0;
        for (var bi = 0; bi < (blocks || []).length; bi++) {
            var block = blocks[bi];
            var qs = block.questions || [];
            if (!qs.length) continue;
            var itemsHtml = '';
            for (var qi = 0; qi < qs.length; qi++) {
                var q = qs[qi];
                var qid = q.id;
                var picked = answersMap[qid];
                if (picked == null || picked === '') continue;
                userNum += 1;
                var ansLbl = choiceLabelForQuestion(q, picked);
                itemsHtml +=
                    '<div class="profile-complete-item profile-complete-item--wide">' +
                    '<span class="profile-complete-label">Вопрос ' +
                    userNum +
                    '</span>' +
                    '<span class="profile-complete-value">' +
                    esc(q.text || '') +
                    '</span>' +
                    '<span class="profile-complete-value muted" style="margin-top:0.35rem">' +
                    esc(String(picked) + '. ' + ansLbl) +
                    '</span></div>';
            }
            if (!itemsHtml) continue;
            var title = String(block.title || '').trim();
            sectionsHtml +=
                '<section class="profile-complete-block">' +
                (title
                    ? '<h3 class="profile-complete-block-title">' + esc(title) + '</h3>'
                    : '') +
                '<div class="profile-complete-grid">' +
                itemsHtml +
                '</div></section>';
        }
        return (
            '<p class="profile-complete-lead muted">' +
            esc(lead) +
            '</p>' +
            (sectionsHtml || '<p class="muted">Нет сохранённых ответов.</p>')
        );
    }

    function quizAnswersListToMap(list) {
        var m = {};
        (list || []).forEach(function (a) {
            if (a && a.question_id != null) m[a.question_id] = a.choice;
        });
        return m;
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
                var fieldLabel = String(f.label || '').trim();
                var labelHtml = fieldLabel
                    ? '<span class="profile-complete-label">' + esc(fieldLabel) + '</span>'
                    : '';
                itemsHtml +=
                    '<div class="profile-complete-item' +
                    wide +
                    (fieldLabel ? '' : ' profile-complete-item--no-label') +
                    '">' +
                    labelHtml +
                    '<span class="profile-complete-value">' +
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

    function questionnaireAudience(educationDetail) {
        var d = String(educationDetail || '').trim().toLowerCase();
        if (d === 'school_8_11' || d === 'school_9' || d === 'school_11') return 'school';
        return 'career';
    }

    function resolveProfileSchema(schema, audienceOrProfile) {
        if (!schema) return { sections: [], completion: {} };
        var audience;
        if (typeof audienceOrProfile === 'string') {
            var s = audienceOrProfile.trim();
            if (s === 'school' || s === 'career') {
                audience = s;
            } else {
                audience = questionnaireAudience(s);
            }
        } else {
            audience = questionnaireAudience(
                (audienceOrProfile && audienceOrProfile.education_detail) || ''
            );
        }
        var completions = schema.completions || {};
        var comp = completions[audience] || schema.completion || {};
        var sectionsOut = [];
        var sections = schema.sections || [];
        for (var si = 0; si < sections.length; si++) {
            var sec = sections[si];
            var secAud = sec.audience;
            if (secAud) {
                var secList = Array.isArray(secAud) ? secAud : [secAud];
                if (secList.indexOf(audience) < 0) continue;
            }
            var fields = [];
            var rawFields = sec.fields || [];
            for (var fi = 0; fi < rawFields.length; fi++) {
                var f = rawFields[fi];
                var fAud = f.audience;
                if (fAud) {
                    var fList = Array.isArray(fAud) ? fAud : [fAud];
                    if (fList.indexOf(audience) < 0) continue;
                }
                fields.push(f);
            }
            if (!fields.length) continue;
            sectionsOut.push(Object.assign({}, sec, { fields: fields }));
        }
        return Object.assign({}, schema, {
            audience: audience,
            completion: comp,
            sections: sectionsOut,
        });
    }

    function parseFavoriteSubjects(profile) {
        if (!profile) return [];
        var raw = profile.favorite_subjects;
        if (!raw) return [];
        if (Array.isArray(raw)) return raw.filter(Boolean);
        var s = String(raw).trim();
        if (!s) return [];
        if (s.charAt(0) === '[') {
            try {
                var arr = JSON.parse(s);
                if (Array.isArray(arr)) return arr.map(String).filter(Boolean);
            } catch (e) {}
        }
        return s
            .split(',')
            .map(function (x) {
                return x.trim();
            })
            .filter(Boolean);
    }

    function parseInterestSpheres(profile) {
        if (!profile) return [];
        const raw = profile.interest_spheres;
        if (!raw) {
            return profile.main_sphere ? [String(profile.main_sphere)] : [];
        }
        if (Array.isArray(raw)) return raw.filter(Boolean);
        const s = String(raw).trim();
        if (!s) return profile.main_sphere ? [String(profile.main_sphere)] : [];
        if (s.charAt(0) === '[') {
            try {
                const arr = JSON.parse(s);
                if (Array.isArray(arr)) return arr.map(String).filter(Boolean);
            } catch (e) {}
        }
        return s
            .split(',')
            .map(function (x) {
                return x.trim();
            })
            .filter(Boolean);
    }

    var EDUCATION_RU_TO_DETAIL = {
        школа: 'school_8_11',
        колледж: 'spo',
        вуз: 'univ_bachelor',
    };

    function normalizeProfileForCompletion(profile) {
        const p = Object.assign({}, profile || {});
        if (!String(p.education_detail || '').trim()) {
            var eduRaw = p.education_level || p.education;
            if (eduRaw != null && String(eduRaw).trim()) {
                var ek = String(eduRaw).trim().toLowerCase();
                if (EDUCATION_RU_TO_DETAIL[ek]) p.education_detail = EDUCATION_RU_TO_DETAIL[ek];
                else if (String(eduRaw).indexOf('_') >= 0) p.education_detail = String(eduRaw).trim();
            }
        }
        if (!String(p.course_grade || '').trim() && p.course_or_grade != null && p.course_or_grade !== '') {
            p.course_grade = String(p.course_or_grade).trim();
        }
        if (!String(p.work_format_preference || '').trim()) {
            const wfp = p.work_format_pref;
            if (Array.isArray(wfp) && wfp.length) p.work_format_preference = String(wfp[0]).trim();
            else if (typeof wfp === 'string' && wfp.trim()) p.work_format_preference = wfp.split(',')[0].trim();
        }
        if (!String(p.education_detail || '').trim() && String(p.education_level || '').trim()) {
            p.education_detail = String(p.education_level).trim();
        }
        if (!String(p.like_to_do || '').trim() && String(p.interests || '').trim()) {
            p.like_to_do = String(p.interests).trim();
        }
        return p;
    }

    function valueFilled(v) {
        if (v == null || v === '') return false;
        if (typeof v === 'number') return !isNaN(v);
        if (typeof v === 'string') return !!v.trim();
        return true;
    }

    function isProfileFieldFilled(profile, fieldId) {
        const p = normalizeProfileForCompletion(profile);
        if (!p) return false;
        if (fieldId === 'favorite_subjects') {
            return parseFavoriteSubjects(p).length > 0;
        }
        if (fieldId === 'interest_spheres') {
            return parseInterestSpheres(p).length > 0;
        }
        if (fieldId === 'course_grade') {
            return valueFilled(p.course_grade) || valueFilled(p.course_or_grade);
        }
        if (fieldId === 'work_format_preference') {
            return valueFilled(p.work_format_preference) || valueFilled(p.work_format_pref);
        }
        if (fieldId === 'education_detail') {
            return valueFilled(p.education_detail) || valueFilled(p.education_level);
        }
        if (fieldId === 'like_to_do') {
            return valueFilled(p.like_to_do) || valueFilled(p.interests);
        }
        return valueFilled(p[fieldId]);
    }

    function isProfileCompleteCheck(schema, profile) {
        const resolved = resolveProfileSchema(schema, profile);
        const p = normalizeProfileForCompletion(profile);
        const comp = resolved && resolved.completion;
        if (comp && comp.required && comp.required.length) {
            for (let i = 0; i < comp.required.length; i++) {
                if (!isProfileFieldFilled(p, comp.required[i])) return false;
            }
            const anyOf = comp.any_of || comp.anyOf || [];
            for (let g = 0; g < anyOf.length; g++) {
                const group = anyOf[g];
                if (!group.some(function (fid) { return isProfileFieldFilled(p, fid); })) return false;
            }
            return true;
        }
        return false;
    }

    function listIncompleteProfileFields(schema, profile) {
        const resolved = resolveProfileSchema(schema, profile);
        const p = normalizeProfileForCompletion(profile);
        const comp = resolved && resolved.completion;
        const missing = [];
        if (!comp || !comp.required) return missing;
        for (let i = 0; i < comp.required.length; i++) {
            const fid = comp.required[i];
            if (!isProfileFieldFilled(p, fid)) missing.push(fid);
        }
        const anyOf = comp.any_of || comp.anyOf || [];
        for (let g = 0; g < anyOf.length; g++) {
            const group = anyOf[g];
            if (!group.some(function (fid) { return isProfileFieldFilled(p, fid); })) {
                missing.push(group[0]);
            }
        }
        return missing;
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
        PROFILE_DRAFT_LEGACY: PROFILE_DRAFT_LEGACY,
        profileDraftKey: profileDraftKey,
        clearLegacyProfileDraft: clearLegacyProfileDraft,
        clearProfileDraftForUser: clearProfileDraftForUser,
        rememberActiveUserId: rememberActiveUserId,
        readActiveUserId: readActiveUserId,
        courseGradeOptionsForEducation: courseGradeOptionsForEducation,
        syncCourseGradeField: syncCourseGradeField,
        wireEducationDetailForCourseGrade: wireEducationDetailForCourseGrade,
        buildProfileSummaryHtml: buildProfileSummaryHtml,
        buildQuizSummaryHtml: buildQuizSummaryHtml,
        quizAnswersListToMap: quizAnswersListToMap,
        choiceLabelForQuestion: choiceLabelForQuestion,
        isNewAccountOnboarding: isNewAccountOnboarding,
        setNewAccountOnboardingFlag: setNewAccountOnboardingFlag,
        clearNewAccountOnboardingFlag: clearNewAccountOnboardingFlag,
        normalizeProfileForCompletion: normalizeProfileForCompletion,
        isProfileFieldFilled: isProfileFieldFilled,
        isProfileCompleteCheck: isProfileCompleteCheck,
        listIncompleteProfileFields: listIncompleteProfileFields,
        parseInterestSpheres: parseInterestSpheres,
        parseFavoriteSubjects: parseFavoriteSubjects,
        questionnaireAudience: questionnaireAudience,
        resolveProfileSchema: resolveProfileSchema,
    };
})(typeof window !== 'undefined' ? window : this);
