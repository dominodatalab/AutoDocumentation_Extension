"""All JavaScript code for the AutoDoc Studio wizard UI."""

from __future__ import annotations


MAIN_DOM_JS = r"""
    // ── Shared fetch helper ──────────────────────────────────────────
    function _checkResp(r) {
        if (!r.ok) throw new Error('Server error (' + r.status + ')');
        return r;
    }

    // ── URL prefixing for Domino app proxy ──────────────────────────
    var _AD_APP_BASE = (function() {
        var m = (window.location.pathname || '').match(/^(\/apps(?:-internal)?\/[^/]+)/i);
        return m ? m[1] + '/' : '';
    })();
    function _adUrl(rel) {
        if (!_AD_APP_BASE) return rel;
        return _AD_APP_BASE + (rel.charAt(0) === '/' ? rel.slice(1) : rel);
    }
    function _adApplyPrefix(root) {
        var scope = root || document;
        scope.querySelectorAll('[data-app-rel]').forEach(function(el) {
            var rel = el.getAttribute('data-app-rel');
            if (!rel) return;
            var full = _adUrl(rel);
            if (el.tagName === 'A') el.setAttribute('href', full);
            else if (el.tagName === 'FORM') el.setAttribute('action', full);
        });
    }
    document.addEventListener('DOMContentLoaded', function() { _adApplyPrefix(); });

    document.addEventListener('DOMContentLoaded', function() {

        // ── Info tooltip ───────────────────────────────────────────────
        (function() {
            var tip = document.createElement('div');
            tip.id = 'studio-info-tooltip';
            tip.setAttribute('role', 'tooltip');
            document.body.appendChild(tip);
            var active = null;
            function hide() { tip.classList.remove('visible'); tip.textContent = ''; active = null; }
            function position() {
                if (!active || !tip.classList.contains('visible')) return;
                var r = active.getBoundingClientRect();
                var gap = 6;
                tip.style.visibility = 'hidden';
                tip.style.display = 'block';
                var tw = tip.offsetWidth, th = tip.offsetHeight;
                var left = r.left + r.width / 2 - tw / 2;
                var top = r.top - th - gap;
                if (top < 8) top = r.bottom + gap;
                left = Math.max(8, Math.min(left, window.innerWidth - tw - 8));
                top = Math.max(8, Math.min(top, window.innerHeight - th - 8));
                tip.style.left = left + 'px';
                tip.style.top = top + 'px';
                tip.style.visibility = '';
            }
            function show(el) {
                if (!el || !el.getAttribute) return;
                if (!el.classList.contains('info-tooltip')) return;
                if (el.classList.contains('env-revision-label-spacer')) return;
                var text = el.getAttribute('data-tooltip');
                if (!text) return;
                active = el;
                tip.textContent = text;
                tip.classList.add('visible');
                position();
            }
            document.addEventListener('mouseover', function(e) {
                var el = e.target && e.target.closest ? e.target.closest('.info-tooltip') : null;
                if (!el) return;
                show(el);
            }, true);
            document.addEventListener('mouseout', function(e) {
                var el = e.target && e.target.closest ? e.target.closest('.info-tooltip') : null;
                if (!el) return;
                var rel = e.relatedTarget;
                if (rel && el.contains(rel)) return;
                hide();
            }, true);
            window.addEventListener('scroll', hide, true);
            window.addEventListener('resize', hide);
        })();

        // ── projectId resolver ─────────────────────────────────────────
        (function() {
            function setProjectId(pid) {
                if (!pid) return;
                try {
                    var u = new URL(window.location.href);
                    if (u.searchParams.get('projectId') === pid) return;
                    u.searchParams.set('projectId', pid);
                    window.location.replace(u.toString());
                } catch (e) {}
            }
            var pid = new URLSearchParams(window.location.search).get('projectId');
            if (!pid && window.location.hash) {
                var h = window.location.hash.substring(1);
                if (h.charAt(0) === '?') h = h.substring(1);
                pid = new URLSearchParams(h).get('projectId');
            }
            if (!pid && window.parent !== window) {
                try {
                    var pLoc = window.parent.location;
                    pid = new URLSearchParams(pLoc.search).get('projectId');
                    if (!pid && pLoc.hash) {
                        var ph = pLoc.hash.substring(1);
                        if (ph.charAt(0) === '?') ph = ph.substring(1);
                        pid = new URLSearchParams(ph).get('projectId');
                    }
                } catch(e) {}
            }
            if (pid) { setProjectId(pid); }
            window.addEventListener('message', function(e) {
                if (e.data && typeof e.data === 'object' && e.data.projectId) {
                    setProjectId(e.data.projectId);
                }
            });
        })();

        function resolvedProjectId() {
            var params = new URLSearchParams(window.location.search);
            return params.get('projectId') || params.get('project_id') || '';
        }

        // ── Language detection ─────────────────────────────────────────
        var langRow = document.getElementById('lang-detection-row');
        var langName = document.getElementById('lang-detected-name');
        var langCount = document.getElementById('lang-detected-count');
        var langInput = document.getElementById('field-detected-language');
        var langSelect = document.getElementById('lang-override-select');
        var langFieldMain = document.getElementById('field-language');

        function detectLanguage(codeRoot) {
            var url = _adUrl('api/detect-language');
            if (codeRoot) url += '?code_root=' + encodeURIComponent(codeRoot);
            fetch(url)
                .then(_checkResp).then(function(r) { return r.json(); })
                .then(function(data) {
                    if (langRow) langRow.style.display = '';
                    if (data.language) {
                        if (langName) langName.textContent = data.display_name;
                        if (langCount) langCount.textContent = '(' + data.file_count + ' files)';
                        if (langInput) langInput.value = data.language;
                        if (langSelect) langSelect.value = data.language;
                    } else {
                        if (langName) langName.textContent = '';
                        if (langCount) langCount.textContent = '';
                        if (langRow) {
                            langRow.innerHTML = '<span class="lang-empty-state">No supported source files found. Supports Python, R, SAS, MATLAB.</span>';
                            langRow.style.display = '';
                        }
                    }
                })
                .catch(function() {});
        }

        window.handleLanguageOverride = function(lang) {
            if (langInput) langInput.value = lang === 'auto' ? 'python' : lang;
            if (langFieldMain) langFieldMain.value = lang;
            var cr = document.getElementById('field-code_root');
            detectLanguage(cr ? cr.value : undefined);
        };

        if (langFieldMain) {
            langFieldMain.addEventListener('change', function() {
                var v = this.value || 'auto';
                if (langInput) langInput.value = v === 'auto' ? 'python' : v;
                if (langSelect) langSelect.value = v;
            });
        }

        function detectLanguageFromCodeRoot() {
            var cr = document.getElementById('field-code_root');
            var val = cr ? (cr.value || '').trim() : '';
            if (!val) {
                if (langRow) langRow.style.display = 'none';
                if (langName) langName.textContent = '';
                if (langCount) langCount.textContent = '';
                return;
            }
            detectLanguage(val);
        }
        detectLanguageFromCodeRoot();

        // ── Provider / model toggles ───────────────────────────────────
        var providerSelect = document.getElementById('field-provider');
        var OPENAI_DEFAULT_MODEL = 'gpt-5.4-mini';
        var ANTHROPIC_DEFAULT_MODEL = 'claude-haiku-4-5';
        function toggleOpenAIFields() {
            var isOpenAI = providerSelect && providerSelect.value === 'openai';
            var pbuInput = document.getElementById('field-provider_base_url');
            if (pbuInput) {
                var dkey = isOpenAI ? 'data-default-openai' : 'data-default-anthropic';
                var dflt = pbuInput.getAttribute(dkey);
                if (dflt) pbuInput.value = dflt;
            }
            var modelInput = document.getElementById('field-model');
            if (modelInput) {
                modelInput.placeholder = isOpenAI ? OPENAI_DEFAULT_MODEL : ANTHROPIC_DEFAULT_MODEL;
            }
        }
        if (providerSelect) {
            providerSelect.addEventListener('change', toggleOpenAIFields);
            toggleOpenAIFields();
        }

        // ── Notebook path enable/disable ───────────────────────────────
        (function() {
            var nbCb = document.getElementById('field-notebook');
            var pathInput = document.getElementById('field-notebook_path');
            var pathWrap = document.getElementById('notebook-path-field-wrap');
            function syncNotebookPathEnabled() {
                var on = nbCb && nbCb.checked;
                if (pathInput) pathInput.disabled = !on;
                if (pathWrap) pathWrap.classList.toggle('notebook-path-disabled', !on);
            }
            if (nbCb) nbCb.addEventListener('change', syncNotebookPathEnabled);
            syncNotebookPathEnabled();
        })();

        // ── Code root options ──────────────────────────────────────────
        (function() {
            var prefix = document.getElementById('code-root-prefix');
            var suffix = document.getElementById('code-root-suffix');
            var hidden = document.getElementById('field-code_root');
            function basePath() {
                if (!prefix) return '';
                if (prefix.tagName === 'SELECT') return (prefix.value || '').trim();
                return (prefix.textContent || '').trim();
            }
            function sync() {
                if (!hidden) return;
                var base = basePath();
                var sub = suffix ? suffix.value.replace(/^\/+/, '') : '';
                hidden.value = sub ? base + '/' + sub : base;
            }
            function showCodeRootError() {
                if (!prefix || prefix.tagName !== 'SELECT') return;
                prefix.innerHTML = '';
                var opt = document.createElement('option');
                opt.value = ''; opt.textContent = 'Could not retrieve source code';
                opt.disabled = true; opt.selected = true;
                prefix.appendChild(opt);
                prefix.classList.remove('code-root-loading');
                prefix.classList.add('code-root-error');
                if (hidden) hidden.value = '';
                sync(); detectLanguageFromCodeRoot();
            }
            function loadCodeRootOptions() {
                if (!prefix || prefix.tagName !== 'SELECT') return;
                var pid = resolvedProjectId();
                if (!pid) { showCodeRootError(); return; }
                var url = _adUrl('api/code-root-options') + '?projectId=' + encodeURIComponent(pid);
                fetch(url)
                    .then(_checkResp).then(function(r) { return r.json(); })
                    .then(function(data) {
                        if (data && data.error) { showCodeRootError(); return; }
                        var opts = (data && data.options) || [];
                        var defRoot = (data && data.defaultRoot) || (opts[0] && opts[0].value) || '';
                        if (!opts.length) { showCodeRootError(); return; }
                        prefix.classList.remove('code-root-error', 'code-root-loading');
                        prefix.innerHTML = '';
                        for (var i = 0; i < opts.length; i++) {
                            var o = opts[i];
                            var opt = document.createElement('option');
                            opt.value = o.value || ''; opt.textContent = o.label || o.value || '';
                            prefix.appendChild(opt);
                        }
                        var found = false;
                        for (var j = 0; j < prefix.options.length; j++) {
                            if (prefix.options[j].value === defRoot) { prefix.selectedIndex = j; found = true; break; }
                        }
                        if (!found) prefix.selectedIndex = 0;
                        sync(); detectLanguageFromCodeRoot();
                    })
                    .catch(function() { showCodeRootError(); });
            }
            if (suffix) {
                suffix.addEventListener('input', sync);
                var langTimer = null;
                suffix.addEventListener('input', function() {
                    clearTimeout(langTimer);
                    langTimer = setTimeout(function() { detectLanguageFromCodeRoot(); }, 400);
                });
            }
            if (prefix && prefix.tagName === 'SELECT') {
                prefix.addEventListener('change', function() { sync(); detectLanguageFromCodeRoot(); });
            }
            sync();
            loadCodeRootOptions();
        })();

        // ── Environment revision reload ────────────────────────────────
        window.reloadEnvironmentRevisions = function(sel) {
            var envId = sel && sel.value ? sel.value : '';
            var slot = document.getElementById('environment-revision-slot');
            if (!slot) return;
            if (!envId) {
                slot.innerHTML = '<select name="environment_revision_id" id="field-environment_revision_id" class="env-revision-select">'
                    + '<option value="" selected disabled>(select environment first)</option></select>';
                return;
            }
            var pid = resolvedProjectId();
            if (!pid) return;
            var url = _adUrl('api/environment-revisions') + '?projectId=' + encodeURIComponent(pid)
                + '&environmentId=' + encodeURIComponent(envId);
            fetch(url).then(_checkResp).then(function(r) { return r.json(); })
                .then(function(revs) {
                    var html = '<select name="environment_revision_id" id="field-environment_revision_id" class="env-revision-select">';
                    if (!revs || !revs.length) {
                        html += '<option value="" selected disabled>(no revisions)</option>';
                    } else {
                        for (var i = 0; i < revs.length; i++) {
                            html += '<option value="' + revs[i].id + '"' + (revs[i].isDefault ? ' selected' : '') + '>'
                                + revs[i].label + '</option>';
                        }
                    }
                    html += '</select>';
                    slot.innerHTML = html;
                })
                .catch(function() {});
        };

        // ═══════════════════════════════════════════════════════════════
        // WIZARD STATE
        // ═══════════════════════════════════════════════════════════════

        var _builtinTemplates = [];      // loaded from API
        var _selectedTemplateSlug = null;  // currently selected template slug
        var _customSpecSelected = false;  // user selected a file from dataset browser

        // Dataset state (shared between spec browser and form submission)
        var _specDatasets = [];
        var _specCurrentDatasetId = '';
        var _specCurrentDatasetName = '';
        var _specCurrentSnapshotId = '';
        var _specCurrentDatasetPath = '';
        var _specCurrentPath = '';
        var _specBrowseAbort = null;

        // Always use spacious layout: drawer history + inline preview
        var _layoutMode = 'B';

        function _applyLayoutMode() {
            var historyDetails = document.getElementById('history-details');
            if (historyDetails) historyDetails.style.display = 'none';
            renderHistoryBtn();
        }

        function renderHistoryBtn() {
            var slot = document.getElementById('history-btn-slot');
            if (!slot) return;
            slot.innerHTML = '<button type="button" id="history-drawer-open-btn" class="history-drawer-btn">'
                + '<span class="material-symbols-outlined">history</span>History'
                + '</button>';
            var btn = slot.querySelector('#history-drawer-open-btn');
            if (btn) btn.addEventListener('click', openHistoryDrawer);
        }

        // ── Drawer open/close ──────────────────────────────────────────
        function openHistoryDrawer() {
            var overlay = document.getElementById('history-drawer-overlay');
            var drawer = document.getElementById('history-drawer');
            if (overlay) overlay.classList.add('open');
            if (drawer) drawer.classList.add('open');
        }

        function closeHistoryDrawer() {
            var overlay = document.getElementById('history-drawer-overlay');
            var drawer = document.getElementById('history-drawer');
            if (overlay) overlay.classList.remove('open');
            if (drawer) drawer.classList.remove('open');
        }

        (function() {
            var closeBtn = document.getElementById('history-drawer-close');
            if (closeBtn) closeBtn.addEventListener('click', closeHistoryDrawer);
            var overlay = document.getElementById('history-drawer-overlay');
            if (overlay) overlay.addEventListener('click', closeHistoryDrawer);
        })();

        // ── Advanced options modal ─────────────────────────────────────
        (function() {
            var overlay = document.getElementById('adv-opts-overlay');
            var openBtn = document.getElementById('adv-opts-open-btn');
            var closeBtn = document.getElementById('adv-opts-close-btn');
            var doneBtn = document.getElementById('adv-opts-done-btn');
            function open() { if (overlay) overlay.classList.add('open'); }
            function close() { if (overlay) overlay.classList.remove('open'); }
            if (openBtn) openBtn.addEventListener('click', open);
            if (closeBtn) closeBtn.addEventListener('click', close);
            if (doneBtn) doneBtn.addEventListener('click', close);
            if (overlay) overlay.addEventListener('click', function(e) {
                if (e.target === overlay) close();
            });
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') close();
            });
        })();

        // ── Browse spec modal ──────────────────────────────────────────
        var _browseSelectedFile = null;

        function openBrowseModal() {
            var overlay = document.getElementById('browse-modal-overlay');
            if (overlay) overlay.classList.add('open');
        }
        window.openBrowseModal = openBrowseModal;

        function closeBrowseModal() {
            var overlay = document.getElementById('browse-modal-overlay');
            if (overlay) overlay.classList.remove('open');
        }
        window.closeBrowseModal = closeBrowseModal;

        function selectBrowseFile(el) {
            document.querySelectorAll('.browse-item-file').forEach(function(r) {
                r.classList.remove('browse-item-selected');
            });
            el.classList.add('browse-item-selected');
            _browseSelectedFile = el.dataset.filename;
            var label = document.getElementById('browse-selected-label');
            if (label) label.textContent = _browseSelectedFile;
            var btn = document.getElementById('browse-confirm-btn');
            if (btn) btn.disabled = false;
        }
        window.selectBrowseFile = selectBrowseFile;

        function confirmBrowseSelection() {
            if (!_browseSelectedFile) return;
            _showSpecConfirm(_browseSelectedFile, 'browse');
            closeBrowseModal();
        }
        window.confirmBrowseSelection = confirmBrowseSelection;

        // ── Upload YAML spec ───────────────────────────────────────────
        var _uploadedSpecFile = null;

        function handleYamlUpload(input) {
            var file = input.files && input.files[0];
            if (!file) return;
            _uploadedSpecFile = file;
            _showSpecConfirm(file.name, 'upload');
            input.value = '';
        }
        window.handleYamlUpload = handleYamlUpload;

        function removeUploadedSpec() {
            _uploadedSpecFile = null;
            _browseSelectedFile = null;
            var bar = document.getElementById('spec-confirm-bar');
            if (bar) { bar.style.display = 'none'; bar.innerHTML = ''; }
        }
        window.removeUploadedSpec = removeUploadedSpec;

        function _showSpecConfirm(filename, source) {
            var bar = document.getElementById('spec-confirm-bar');
            if (!bar) return;
            var icon = source === 'upload' ? 'upload_file' : 'description';
            bar.innerHTML =
                '<span class="spec-confirm-icon material-symbols-outlined">' + icon + '</span>' +
                '<span class="spec-confirm-name">' + filename + '</span>' +
                '<span class="spec-confirm-source">' + (source === 'upload' ? 'Uploaded' : 'From dataset') + '</span>' +
                '<button type="button" class="spec-confirm-remove" onclick="removeUploadedSpec()" title="Remove">' +
                '  <span class="material-symbols-outlined" style="font-size:15px">close</span>' +
                '</button>';
            bar.style.display = 'flex';
        }

        // ── Wizard navigation ──────────────────────────────────────────
        function showStep1() {
            var s1 = document.getElementById('wizard-step1');
            var s2 = document.getElementById('wizard-step2');
            if (s1) s1.style.display = '';
            if (s2) s2.style.display = 'none';
            closeHistoryDrawer();
        }

        function showStep2() {
            var s1 = document.getElementById('wizard-step1');
            var s2 = document.getElementById('wizard-step2');
            if (s1) s1.style.display = 'none';
            if (s2) s2.style.display = '';
            _applyLayoutMode();
        }

        var backBtn = document.getElementById('btn-back-to-templates');
        if (backBtn) {
            backBtn.addEventListener('click', function() {
                showStep1();
            });
        }

        // ── Generate button state ──────────────────────────────────────
        function updateGenerateButton() {
            var btn = document.getElementById('generate-btn');
            if (!btn) return;
            var hasTemplate = !!_selectedTemplateSlug;
            var hasCustomSpec = _customSpecSelected;
            var canGenerate = hasTemplate || hasCustomSpec;
            btn.disabled = !canGenerate;

        }

        // ── Template gallery ───────────────────────────────────────────
        function loadBuiltinTemplates() {
            var pid = resolvedProjectId();
            var url = _adUrl('api/built-in-templates');
            if (pid) url += '?projectId=' + encodeURIComponent(pid);
            fetch(url)
                .then(_checkResp).then(function(r) { return r.json(); })
                .then(function(templates) {
                    _builtinTemplates = templates;
                    renderTemplateGallery(templates);
                })
                .catch(function() {
                    var gallery = document.getElementById('template-gallery');
                    if (gallery) {
                        gallery.innerHTML = '<div class="gallery-loading">'
                            + '<span class="material-symbols-outlined gallery-loading-icon">error</span>'
                            + '<span class="gallery-loading-text">Could not load templates.</span>'
                            + '</div>';
                    }
                });
        }

        function _esc(s) {
            return String(s || '')
                .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
        }

        function renderTemplateGallery(templates) {
            var gallery = document.getElementById('template-gallery');
            if (!gallery) return;
            if (!templates || !templates.length) {
                gallery.innerHTML = '<div class="gallery-loading"><span class="gallery-loading-text">No templates found.</span></div>';
                return;
            }
            var html = '';
            for (var i = 0; i < templates.length; i++) {
                var t = templates[i];
                var sectionCount = (t.sections || []).length;
                html += '<div class="template-card" data-slug="' + _esc(t.slug) + '" tabindex="0" role="button" aria-pressed="false">'
                    + '<div class="template-card-header">'
                    + '<span class="template-card-name">' + _esc(t.name) + '</span>'
                    + '<span class="material-symbols-outlined template-card-check">check_circle</span>'
                    + '</div>'
                    + '<p class="template-card-desc">' + _esc(t.description) + '</p>'
                    + '<div class="template-card-meta">'
                    + '<span class="template-card-badge">' + sectionCount + ' sections</span>'
                    + '</div>'
                    + '</div>';
            }
            gallery.innerHTML = html;

            // Wire click/keyboard handlers
            var cards = gallery.querySelectorAll('.template-card');
            for (var j = 0; j < cards.length; j++) {
                (function(card) {
                    card.addEventListener('click', function() {
                        selectTemplate(card.getAttribute('data-slug'));
                    });
                    card.addEventListener('keydown', function(e) {
                        if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            selectTemplate(card.getAttribute('data-slug'));
                        }
                    });
                })(cards[j]);
            }
        }

        function selectTemplate(slug) {
            _selectedTemplateSlug = slug;
            _customSpecSelected = false;

            // Update card UI
            var cards = document.querySelectorAll('.template-card');
            for (var i = 0; i < cards.length; i++) {
                var isSelected = cards[i].getAttribute('data-slug') === slug;
                cards[i].classList.toggle('selected', isSelected);
                cards[i].setAttribute('aria-pressed', isSelected ? 'true' : 'false');
            }

            // Render preview
            var tpl = null;
            for (var j = 0; j < _builtinTemplates.length; j++) {
                if (_builtinTemplates[j].slug === slug) { tpl = _builtinTemplates[j]; break; }
            }
            if (tpl) renderTemplatePreview(tpl);

            updateGenerateButton();
        }

        function renderTemplatePreview(tpl) {
            var panel = document.getElementById('template-preview-panel');
            if (!panel) return;
            var sections = tpl.sections || [];
            var perModel = tpl.per_model_sections || [];
            var perModelSet = {};
            for (var k = 0; k < perModel.length; k++) perModelSet[perModel[k]] = true;

            var sectionsHtml = '';
            for (var i = 0; i < sections.length; i++) {
                var badge = perModelSet[sections[i]]
                    ? '<span class="preview-section-badge">once per model</span>' : '';
                sectionsHtml += '<div class="preview-section-item">'
                    + '<span class="preview-section-num">' + (i + 1) + '</span>'
                    + '<span class="preview-section-name">' + _esc(sections[i]) + '</span>'
                    + badge
                    + '</div>';
            }

            panel.innerHTML = '<div class="preview-header">'
                + '<div class="preview-title">' + _esc(tpl.name) + '</div>'
                + '<div class="preview-description">' + _esc(tpl.description) + '</div>'
                + '</div>'
                + '<div class="preview-sections">' + sectionsHtml + '</div>';
        }

        // ── Dataset auto-resolution ────────────────────────────────────
        // The project's autodoc dataset is resolved automatically from the
        // project ID — no user selection required.
        var specFileList = document.getElementById('spec-file-list');
        var specBreadcrumb = document.getElementById('spec-breadcrumb');
        var specMachineUpload = document.getElementById('spec-machine-upload');
        var specUploadStatus = document.getElementById('spec-upload-status');
        var specPathField = document.getElementById('field-spec_path');

        function queryApiDatasetFiles(relPath) {
            var parts = [];
            var pid = resolvedProjectId();
            if (pid) parts.push('projectId=' + encodeURIComponent(pid));
            if (_specCurrentDatasetId) parts.push('datasetId=' + encodeURIComponent(_specCurrentDatasetId));
            if (_specCurrentSnapshotId) parts.push('snapshotId=' + encodeURIComponent(_specCurrentSnapshotId));
            if (relPath) parts.push('path=' + encodeURIComponent(relPath));
            return parts.length ? ('?' + parts.join('&')) : '?';
        }

        function queryJobHistory() {
            var parts = [];
            var pid = resolvedProjectId();
            if (pid) parts.push('projectId=' + encodeURIComponent(pid));
            if (_specCurrentDatasetId) parts.push('datasetId=' + encodeURIComponent(_specCurrentDatasetId));
            if (_specCurrentSnapshotId) parts.push('snapshotId=' + encodeURIComponent(_specCurrentSnapshotId));
            return parts.length ? ('?' + parts.join('&')) : '';
        }

        function _applyDataset(ds) {
            _specCurrentDatasetId   = ds.id   || '';
            _specCurrentDatasetName = ds.name  || '';
            _specCurrentSnapshotId  = ds.rwSnapshotId  || '';
            _specCurrentDatasetPath = ds.datasetPath   || '';
            _specCurrentPath = '';
            if (specPathField && !_selectedTemplateSlug) specPathField.value = '';
            if (_specCurrentDatasetId) {
                browseFiles('');
            }
            updateGenerateButton();
        }

        function loadDatasets() {
            var pid = resolvedProjectId();
            if (!pid) return;
            fetch(_adUrl('api/datasets') + '?projectId=' + encodeURIComponent(pid))
                .then(_checkResp).then(function(r) { return r.json(); })
                .then(function(datasets) {
                    if (!datasets || datasets.error || !datasets.length) return;
                    _specDatasets = datasets;
                    // Prefer a dataset named 'autodoc', otherwise use the first one
                    var chosen = datasets[0];
                    for (var i = 0; i < datasets.length; i++) {
                        if (datasets[i].name === 'autodoc') { chosen = datasets[i]; break; }
                    }
                    _applyDataset(chosen);
                    fetchJobHistory();
                })
                .catch(function() { /* silently ignore — dataset is optional for template-based flow */ });
        }

        loadDatasets();

        // ── Spec file browser ──────────────────────────────────────────
        function specParentPath(p) {
            if (!p) return null;
            var parts = p.split('/').filter(Boolean);
            if (!parts.length) return null;
            parts.pop();
            return parts.join('/');
        }

        function browseFiles(path) {
            _specCurrentPath = path;
            if (!specFileList) return Promise.resolve();
            if (!_specCurrentDatasetId) {
                specFileList.innerHTML = '<div class="spec-file-empty"><span class="spec-file-list-empty">Select a dataset first</span></div>';
                return Promise.resolve();
            }
            renderBreadcrumb(path);
            if (_specBrowseAbort) _specBrowseAbort.abort();
            var ctrl = _specBrowseAbort = new AbortController();
            specFileList.classList.add('spec-file-list-pending');
            return fetch(_adUrl('api/dataset-files') + queryApiDatasetFiles(path), { signal: ctrl.signal })
                .then(_checkResp).then(function(r) { return r.json(); })
                .then(function(files) {
                    if (!Array.isArray(files)) {
                        specFileList.innerHTML = '<div class="spec-file-empty"><span class="spec-file-list-empty">'
                            + (files && files.error ? 'Error: ' + files.error : 'Unexpected response') + '</span></div>';
                        return;
                    }
                    var html = '';
                    var parentPath = specParentPath(path);
                    if (parentPath !== null) {
                        html += '<div class="spec-file-item spec-file-parent" data-path="' + parentPath + '" data-dir="true" data-name=".." data-parent="true">'
                            + '<span class="spec-file-icon">\ud83d\udcc1</span>'
                            + '<span class="spec-file-name">..</span>'
                            + '<span class="spec-file-size"></span></div>';
                    }
                    if (!files.length && parentPath === null) {
                        specFileList.innerHTML = '<div class="spec-file-empty"><span class="spec-file-list-empty">No YAML files found</span></div>';
                        return;
                    }
                    files.sort(function(a, b) {
                        if (a.isDirectory && !b.isDirectory) return -1;
                        if (!a.isDirectory && b.isDirectory) return 1;
                        return a.fileName.localeCompare(b.fileName);
                    });
                    for (var i = 0; i < files.length; i++) {
                        var f = files[i];
                        var icon = f.isDirectory ? '\ud83d\udcc1' : '\ud83d\udcc4';
                        var size = f.isDirectory ? '' : formatBytes(f.sizeInBytes || 0);
                        var fullPath = path ? path + '/' + f.fileName : f.fileName;
                        html += '<div class="spec-file-item" data-path="' + fullPath + '" data-dir="' + f.isDirectory + '" data-name="' + f.fileName + '">'
                            + '<span class="spec-file-icon">' + icon + '</span>'
                            + '<span class="spec-file-name">' + f.fileName + '</span>'
                            + '<span class="spec-file-size">' + size + '</span>'
                            + '</div>';
                    }
                    specFileList.innerHTML = html;
                    var items = specFileList.querySelectorAll('.spec-file-item');
                    for (var j = 0; j < items.length; j++) {
                        items[j].addEventListener('click', onFileClick);
                    }
                })
                .catch(function(err) {
                    if (err && err.name === 'AbortError') return;
                    specFileList.innerHTML = '<div class="spec-file-empty"><span class="spec-file-list-empty">Failed to load files</span></div>';
                })
                .finally(function() {
                    if (specFileList && _specBrowseAbort === ctrl) {
                        specFileList.classList.remove('spec-file-list-pending');
                    }
                });
        }

        function onFileClick(e) {
            var el = e.currentTarget;
            var isDir = el.getAttribute('data-dir') === 'true';
            var path = el.getAttribute('data-path');
            if (isDir) {
                browseFiles(path);
            } else {
                var items = specFileList ? specFileList.querySelectorAll('.spec-file-item') : [];
                for (var i = 0; i < items.length; i++) items[i].classList.remove('selected');
                el.classList.add('selected');
                selectCustomSpecFile(path);
            }
        }

        function absoluteSpecFromRelative(relPath) {
            var base = (_specCurrentDatasetPath || '').replace(/\/+$/, '');
            var rel = (relPath || '').replace(/^\/+/, '');
            if (base) return rel ? (base + '/' + rel) : base;
            if (_specCurrentDatasetName && rel) return 'dataset://' + _specCurrentDatasetName + '/' + rel;
            return rel || '';
        }

        function selectCustomSpecFile(relFilePath) {
            var abs = absoluteSpecFromRelative(relFilePath);
            if (specPathField) specPathField.value = abs;
            _selectedTemplateSlug = null;
            _customSpecSelected = true;
            // Deselect template cards
            var cards = document.querySelectorAll('.template-card');
            for (var i = 0; i < cards.length; i++) {
                cards[i].classList.remove('selected');
                cards[i].setAttribute('aria-pressed', 'false');
            }
            updateGenerateButton();
        }

        function renderBreadcrumb(path) {
            if (!specBreadcrumb) return;
            var parts = path ? path.split('/').filter(Boolean) : [];
            var html = '<span class="spec-breadcrumb-link" onclick="window._specBrowse(\'\')">root</span>';
            var cumulative = '';
            for (var i = 0; i < parts.length; i++) {
                cumulative += (i > 0 ? '/' : '') + parts[i];
                html += '<span class="spec-breadcrumb-sep">/</span>';
                if (i === parts.length - 1) {
                    html += '<span class="spec-breadcrumb-current">' + parts[i] + '</span>';
                } else {
                    html += '<span class="spec-breadcrumb-link" onclick="window._specBrowse(\'' + cumulative + '\')">' + parts[i] + '</span>';
                }
            }
            specBreadcrumb.innerHTML = html;
        }

        function formatBytes(bytes) {
            if (bytes === 0) return '';
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        }

        window._specBrowse = function(path) { browseFiles(path); };

        // ── Machine upload ─────────────────────────────────────────────
        if (specMachineUpload) {
            specMachineUpload.addEventListener('change', function(e) {
                var file = e.target.files[0];
                if (!file) return;
                if (specUploadStatus) { specUploadStatus.textContent = 'Uploading ' + file.name + '...'; }
                var uploadDsId = _specCurrentDatasetId;
                if (!uploadDsId) {
                    if (specUploadStatus) { specUploadStatus.textContent = 'Select a dataset first'; }
                    return;
                }
                var _pid = resolvedProjectId();
                var qs = _pid ? ('?projectId=' + encodeURIComponent(_pid)) : '';
                var fd = new FormData();
                fd.append('datasetId', uploadDsId);
                fd.append('relativeDir', _specCurrentPath || '');
                fd.append('file', file);
                fetch(_adUrl('api/upload-spec-to-dataset') + qs, { method: 'POST', body: fd })
                    .then(_checkResp).then(function(r) { return r.json(); })
                    .then(function(result) {
                        if (result.error) throw new Error(result.error);
                        if (specUploadStatus) { specUploadStatus.textContent = 'Uploaded: ' + result.fileName; }
                        selectCustomSpecFile(result.path);
                        browseFiles(_specCurrentPath);
                    })
                    .catch(function(err) {
                        if (specUploadStatus) { specUploadStatus.textContent = 'Upload failed: ' + err.message; }
                    })
                    .finally(function() { specMachineUpload.value = ''; });
            });
        }

        // ── Spec validation helper ────────────────────────────────────
        window._specValid = true;
        function validateSpecContent(file) {
            var fd = new FormData();
            fd.append('spec_upload', file);
            var resultEl = document.getElementById('spec-validation-result');
            if (resultEl) resultEl.innerHTML = '<span class="spec-validation-pending">Validating...</span>';
            fetch(_adUrl('validate-spec'), { method: 'POST', body: fd })
                .then(_checkResp).then(function(r) { return r.json(); })
                .then(function(data) {
                    window._specValid = data.valid;
                    if (!resultEl) return;
                    if (data.valid) {
                        resultEl.innerHTML = '<span class="spec-validation-success">Spec is valid</span>';
                    } else {
                        var items = (data.errors || []).map(function(e) { return '<li>' + e + '</li>'; }).join('');
                        resultEl.innerHTML = '<div class="spec-validation-error">'
                            + '<span>Spec validation failed</span>'
                            + '<ul class="spec-validation-error-list">' + items + '</ul>'
                            + '</div>';
                    }
                })
                .catch(function() { if (resultEl) resultEl.innerHTML = ''; });
        }

        // ═══════════════════════════════════════════════════════════════
        // JOB HISTORY RENDERING
        // ═══════════════════════════════════════════════════════════════

        var _ACTIVE_STATUSES = { queued: true, submitted: true, pending: true, running: true };

        function _jobRow(j) {
            var status = j.status || 'queued';
            var statusCls = 'history-status history-status-' + status;
            var branch = j.branch || '\u2014';
            var submitted = j.submitted_at ? j.submitted_at.slice(0, 16).replace('T', ' ') : '\u2014';
            var jobCell = j.job_url
                ? '<td><a href="' + _esc(j.job_url) + '" target="_blank" rel="noopener">View \u2192</a></td>'
                : '<td>\u2014</td>';
            var isActive = _ACTIVE_STATUSES[status];
            var docCell;
            if (status === 'succeeded' && j.dataset_url) {
                docCell = '<td><a href="' + _esc(j.dataset_url) + '" target="_blank" rel="noopener">Open \u2192</a></td>';
            } else if (isActive) {
                docCell = '<td class="history-pending-cell">Pending\u2026</td>';
            } else {
                docCell = '<td>\u2014</td>';
            }
            return '<tr>'
                + '<td title="' + _esc(branch) + '">' + _esc(branch) + '</td>'
                + '<td><span class="' + statusCls + '">' + _esc(status.toUpperCase()) + '</span></td>'
                + '<td>' + _esc(submitted) + '</td>'
                + jobCell
                + docCell
                + '</tr>';
        }

        function _tableHtml(jobs) {
            var header = '<thead><tr><th>Branch</th><th>Status</th><th>Submitted</th><th>Job</th><th>AutoDoc file</th></tr></thead>';
            var rows = jobs.map(function(j) { return _jobRow(j); }).join('');
            return '<table class="history-table">' + header + '<tbody>' + rows + '</tbody></table>';
        }

        function renderResultsPanel(jobs) {
            var panel = document.getElementById('results-panel');
            if (!panel) return;
            if (!jobs || !jobs.length) return;

            var latestJob = jobs[0];
            var status = latestJob.status || 'queued';

            var html = '<div class="results-job-card">';

            // Header row
            html += '<div class="results-job-header">';
            html += '<div class="results-job-info">';
            if (_selectedTemplateSlug) {
                var tplName = '';
                for (var i = 0; i < _builtinTemplates.length; i++) {
                    if (_builtinTemplates[i].slug === _selectedTemplateSlug) { tplName = _builtinTemplates[i].name; break; }
                }
                if (tplName) html += '<div class="results-job-template">Template</div><div class="results-job-title">' + _esc(tplName) + '</div>';
            } else {
                html += '<div class="results-job-title">Documentation</div>';
            }
            html += '</div>';
            html += '<div class="results-status-col">';
            html += '<span class="terminal-status terminal-status-' + _esc(status) + '">' + _esc(status.toUpperCase()) + '</span>';
            html += '</div>';
            html += '</div>'; // end results-job-header

            // State-specific content
            if (status === 'succeeded') {
                html += '<div class="results-success">';
                var autodocLink = latestJob.dataset_url
                    ? '<a href="' + _esc(latestJob.dataset_url) + '" target="_blank" rel="noopener" class="success-open-btn">'
                        + '<span class="material-symbols-outlined" style="font-size:15px">folder_open</span>Open AutoDoc file</a>'
                    : '';
                html += '<div class="results-success-banner">'
                    + '<span class="material-symbols-outlined results-success-icon">check_circle</span>'
                    + '<div class="results-success-text">'
                    + '<div class="results-success-headline">Documentation generated successfully</div>'
                    + '</div>'
                    + (autodocLink ? autodocLink : '')
                    + '</div>';
                // Inline preview (always spacious layout)
                html += '<div class="doc-preview-inline">'
                    + '<div class="doc-preview-inline-header"><span class="material-symbols-outlined">description</span>Document preview</div>'
                    + '<div id="doc-preview-content" class="doc-preview-content">'
                    + '<div class="doc-preview-loading"><span class="material-symbols-outlined rotating-icon">autorenew</span> Loading preview\u2026</div>'
                    + '</div>'
                    + '</div>';
                html += '</div>';
            } else if (status === 'failed') {
                html += '<div class="results-failed">';
                html += '<div class="results-failed-banner">'
                    + '<span class="material-symbols-outlined results-failed-icon">error</span>'
                    + '<div class="results-failed-text">'
                    + '<div class="results-failed-headline">Generation failed</div>'
                    + '<div class="results-failed-detail">'
                    + (latestJob.domino_status ? _esc(latestJob.domino_status) : 'Check the job logs in Domino for details.')
                    + '</div>'
                    + '</div></div>';
                html += '</div>';
            } else if (status === 'cancelled') {
                html += '<div class="results-failed">'
                    + '<div class="results-failed-banner">'
                    + '<span class="material-symbols-outlined results-failed-icon">cancel</span>'
                    + '<div class="results-failed-text">'
                    + '<div class="results-failed-headline">Job cancelled</div>'
                    + '</div></div></div>';
            } else {
                // running / queued / submitted / pending
                var isQueued = status === 'queued' && !latestJob.domino_run_id;
                html += '<div class="results-running">';
                html += '<div class="results-running-banner">'
                    + '<span class="material-symbols-outlined results-running-spinner">autorenew</span>'
                    + '<div>'
                    + '<div class="results-running-headline">' + (isQueued ? 'Job queued' : 'Generating documentation\u2026') + '</div>'
                    + '<div class="results-running-sub">'
                    + (isQueued
                        ? 'Waiting for a job slot. This will start automatically when one opens.'
                        : 'Scanning code, planning sections, and writing content via LLM.')
                    + '</div>'
                    + '</div></div>';

                // Single animated progress bar
                var _progressStages = ['Scanning code\u2026', 'Planning sections\u2026', 'Generating content\u2026', 'Finalizing document\u2026'];
                var _stageIdx = isQueued ? 0 : (status === 'running' ? 1 : 0);
                html += '<div class="job-progress-wrap">'
                    + '<div class="job-progress-track">'
                    + '<div class="job-progress-fill' + (status === 'running' ? ' animating' : '') + '" id="job-progress-fill"></div>'
                    + '</div>'
                    + '<div class="job-progress-label" id="job-progress-label">' + _progressStages[_stageIdx] + '</div>'
                    + '</div>';

                html += '</div>';
            }

            html += '</div>'; // end results-job-card
            panel.innerHTML = html;

            // Start or stop the progress label cycle
            if (status === 'running' || status === 'submitted' || status === 'pending') {
                _startProgressCycle();
            } else {
                _stopProgressCycle();
            }
        }


        // ═══════════════════════════════════════════════════════════════
        // DOC PREVIEW (mammoth.js)
        // ═══════════════════════════════════════════════════════════════

        function _fetchAndRenderPreview(latestJob, previewContent) {
            var dsId = latestJob.dataset_id || _specCurrentDatasetId;
            var snapId = _specCurrentSnapshotId;
            if (!dsId || !snapId) {
                previewContent.innerHTML = '<p class="doc-preview-error">Dataset not available for preview.</p>';
                return;
            }
            var pid = resolvedProjectId();
            var qs = '?datasetId=' + encodeURIComponent(dsId)
                + '&snapshotId=' + encodeURIComponent(snapId)
                + (pid ? '&projectId=' + encodeURIComponent(pid) : '');
            fetch(_adUrl('api/doc-content') + qs)
                .then(function(r) {
                    if (!r.ok) throw new Error('HTTP ' + r.status);
                    return r.arrayBuffer();
                })
                .then(function(buf) {
                    if (typeof mammoth === 'undefined') {
                        previewContent.innerHTML = '<p class="doc-preview-error">Preview library not loaded.</p>';
                        return;
                    }
                    return mammoth.convertToHtml({ arrayBuffer: buf }).then(function(result) {
                        previewContent.innerHTML = '<div class="doc-preview-body">' + result.value + '</div>';
                    });
                })
                .catch(function(err) {
                    previewContent.innerHTML = '<p class="doc-preview-error">Could not load preview: ' + _esc(String(err)) + '</p>';
                });
        }

        function _attachDocPreview(latestJob) {
            var previewContent = document.getElementById('doc-preview-content');
            if (!previewContent) return;
            _fetchAndRenderPreview(latestJob, previewContent);
        }

        function renderJobHistory(jobs) {
            // Write to the correct container depending on layout mode
            var elA = document.getElementById('job-history-content');        // accordion (Layout A)
            var elB = document.getElementById('job-history-drawer-content'); // drawer   (Layout B)

            function _render(el) {
                if (!el) return;
                if (!jobs || !jobs.length) {
                    el.innerHTML = '<div class="spec-file-empty">'
                        + '<span class="material-symbols-outlined spec-file-empty-icon">description</span>'
                        + '<span class="spec-file-list-empty">No history yet.</span></div>';
                    return;
                }
                var hasQueued = jobs.some(function(j) { return j.status === 'queued' && !j.domino_run_id; });
                var html = '';
                if (hasQueued) {
                    html += '<div class="inline-callout inline-callout-warning" role="alert">'
                        + '\u26a0 Job queued \u2014 waiting for a slot to open.'
                        + '</div>';
                }
                html += '<div class="history-table-wrap">' + _tableHtml(jobs) + '</div>';
                var actions = '<a class="terminal-action" id="job-history-refresh-btn-' + el.id + '" href="#">Refresh</a>';
                if (hasQueued) {
                    actions += ' <a class="terminal-action" id="job-cancel-queued-btn-' + el.id + '" href="#">Cancel queued</a>';
                }
                html += '<div class="history-actions">' + actions + '</div>';
                el.innerHTML = html;

                var refreshBtn = el.querySelector('[id^="job-history-refresh-btn"]');
                if (refreshBtn) refreshBtn.addEventListener('click', function(e) { e.preventDefault(); fetchJobHistory(); });
                var cancelBtn = el.querySelector('[id^="job-cancel-queued-btn"]');
                if (cancelBtn) {
                    cancelBtn.addEventListener('click', function(e) {
                        e.preventDefault();
                        fetch(_adUrl('cancel-queued-jobs') + queryJobHistory(), { method: 'POST' })
                            .then(_checkResp).then(function(r) { return r.json(); })
                            .then(function(data) { onJobsUpdated(data.jobs || []); })
                            .catch(function() {});
                    });
                }
            }

            // Always update both containers so switching layout shows current data
            _render(elA);
            _render(elB);
        }

        function onJobsUpdated(jobs) {
            renderResultsPanel(jobs);
            renderJobHistory(jobs);
            if (jobs && jobs.length && jobs[0].status === 'succeeded') {
                _attachDocPreview(jobs[0]);
            }
        }

        function fetchJobHistory() {
            fetch(_adUrl('job-history') + queryJobHistory())
                .then(_checkResp).then(function(r) { return r.json(); })
                .then(function(data) { onJobsUpdated(data.jobs || []); })
                .catch(function() {});
        }

        // Cycle progress label through stages while job is running
        var _progressInterval = null;
        var _progressStageList = ['Scanning code\u2026', 'Planning sections\u2026', 'Generating content\u2026', 'Finalizing document\u2026'];
        var _progressStageIdx = 0;
        function _startProgressCycle() {
            _progressStageIdx = 0;
            clearInterval(_progressInterval);
            _progressInterval = setInterval(function() {
                _progressStageIdx = Math.min(_progressStageIdx + 1, _progressStageList.length - 1);
                var el = document.getElementById('job-progress-label');
                if (el) el.textContent = _progressStageList[_progressStageIdx];
                if (_progressStageIdx >= _progressStageList.length - 1) clearInterval(_progressInterval);
            }, 5500);
        }
        function _stopProgressCycle() { clearInterval(_progressInterval); }

        // Poll job history every 10 seconds when on step 2
        setInterval(function() {
            var s2 = document.getElementById('wizard-step2');
            if (s2 && s2.style.display !== 'none') {
                fetchJobHistory();
            }
        }, 10000);

        // ═══════════════════════════════════════════════════════════════
        // FORM SUBMISSION
        // ═══════════════════════════════════════════════════════════════

        function showWizardError(msg) {
            var errEl = document.getElementById('wizard-error');
            if (errEl) { errEl.textContent = msg; errEl.style.display = ''; }
        }
        function hideWizardError() {
            var errEl = document.getElementById('wizard-error');
            if (errEl) errEl.style.display = 'none';
        }

        // Save a built-in template YAML to the dataset before submitting
        function saveBuiltinSpec(tpl) {
            return new Promise(function(resolve, reject) {
                if (!_specCurrentDatasetId) {
                    reject(new Error('No dataset selected. Please expand Advanced options and select a dataset.'));
                    return;
                }
                var pid = resolvedProjectId();
                var qs = pid ? ('?projectId=' + encodeURIComponent(pid)
                    + '&datasetId=' + encodeURIComponent(_specCurrentDatasetId)
                    + '&snapshotId=' + encodeURIComponent(_specCurrentSnapshotId))
                    : ('?datasetId=' + encodeURIComponent(_specCurrentDatasetId)
                    + '&snapshotId=' + encodeURIComponent(_specCurrentSnapshotId));

                var fd = new FormData();
                fd.append('spec_filename', tpl.slug + '.yaml');
                fd.append('spec_content', tpl.yaml_content);

                fetch(_adUrl('save-spec') + qs, { method: 'POST', body: fd })
                    .then(_checkResp).then(function(r) { return r.json(); })
                    .then(function(data) {
                        if (data.error) { reject(new Error(data.error)); return; }
                        // data.saved is the absolute path in the dataset
                        resolve(data.saved);
                    })
                    .catch(reject);
            });
        }

        var mainForm = document.getElementById('main-form');
        if (mainForm) {
            mainForm.addEventListener('submit', function(e) {
                e.preventDefault();
                hideWizardError();

                if (!_specCurrentDatasetId) {
                    showWizardError('No dataset selected. Expand Advanced options and select a dataset.');
                    // Open advanced options so user sees it
                    var advOpts = document.getElementById('wizard-advanced-opts');
                    if (advOpts) advOpts.open = true;
                    return;
                }

                var btn = document.getElementById('generate-btn');
                if (btn) btn.disabled = true;

                function doSubmit(specPath) {
                    if (specPathField) specPathField.value = specPath;

                    var fd = new FormData(mainForm);
                    var pid = resolvedProjectId();
                    if (pid && !fd.get('projectId')) fd.append('projectId', pid);
                    if (_specCurrentDatasetId && !fd.get('datasetId')) fd.append('datasetId', _specCurrentDatasetId);
                    if (_specCurrentSnapshotId && !fd.get('snapshotId')) fd.append('snapshotId', _specCurrentSnapshotId);
                    if (_specCurrentDatasetPath && !fd.get('datasetPath')) fd.append('datasetPath', _specCurrentDatasetPath);

                    // Transition to step 2 immediately
                    showStep2();
                    var panel = document.getElementById('results-panel');
                    if (panel) {
                        panel.innerHTML = '<div class="results-submitting">'
                            + '<span class="material-symbols-outlined results-submitting-icon">rocket_launch</span>'
                            + '<span class="results-submitting-text">Submitting job\u2026</span>'
                            + '</div>';
                    }

                    var qs = pid ? ('?projectId=' + encodeURIComponent(pid)) : '';
                    fetch(_adUrl('run') + qs, { method: 'POST', body: fd })
                        .then(_checkResp).then(function(r) { return r.json(); })
                        .then(function(data) {
                            if (data.error) {
                                if (panel) {
                                    panel.innerHTML = '<div class="results-failed">'
                                        + '<div class="results-failed-banner">'
                                        + '<span class="material-symbols-outlined results-failed-icon">error</span>'
                                        + '<div class="results-failed-text">'
                                        + '<div class="results-failed-headline">Submission failed</div>'
                                        + '<div class="results-failed-detail">' + _esc(data.error) + '</div>'
                                        + '</div></div></div>';
                                }
                            }
                            onJobsUpdated(data.jobs || []);
                        })
                        .catch(function(err) {
                            if (panel) {
                                panel.innerHTML = '<div class="results-failed">'
                                    + '<div class="results-failed-banner">'
                                    + '<span class="material-symbols-outlined results-failed-icon">error</span>'
                                    + '<div class="results-failed-text">'
                                    + '<div class="results-failed-headline">Submission failed</div>'
                                    + '<div class="results-failed-detail">' + _esc(err.message || String(err)) + '</div>'
                                    + '</div></div></div>';
                            }
                        })
                        .finally(function() {
                            if (btn) btn.disabled = false;
                            updateGenerateButton();
                        });
                }

                if (_selectedTemplateSlug) {
                    // Find the template and save it to the dataset first
                    var tpl = null;
                    for (var i = 0; i < _builtinTemplates.length; i++) {
                        if (_builtinTemplates[i].slug === _selectedTemplateSlug) { tpl = _builtinTemplates[i]; break; }
                    }
                    if (!tpl) {
                        showWizardError('Selected template not found. Please refresh the page.');
                        if (btn) btn.disabled = false;
                        updateGenerateButton();
                        return;
                    }
                    saveBuiltinSpec(tpl)
                        .then(function(savedPath) { doSubmit(savedPath); })
                        .catch(function(err) {
                            showWizardError('Could not save template: ' + err.message);
                            if (btn) btn.disabled = false;
                            updateGenerateButton();
                        });
                } else if (_customSpecSelected && specPathField && specPathField.value.trim()) {
                    doSubmit(specPathField.value.trim());
                } else {
                    showWizardError('Please select a template or a custom spec file.');
                    if (btn) btn.disabled = false;
                    updateGenerateButton();
                }
            });
        }

        // ── Init ───────────────────────────────────────────────────────
        loadBuiltinTemplates();
        updateGenerateButton();

    }); // end DOMContentLoaded
"""
