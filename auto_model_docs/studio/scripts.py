"""All JavaScript code for the AutoDoc Studio wizard UI."""

from __future__ import annotations


MAIN_DOM_JS = r"""
    // ── Shared fetch helper ──────────────────────────────────────────
    function _checkResp(r) {
        if (r.ok) return r;
        return r.text().then(function(txt) {
            try {
                var data = JSON.parse(txt);
                if (data && data.error) throw new Error(data.error);
            } catch (e) {}
            throw new Error(txt || ('Server error (' + r.status + ')'));
        });
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


        // ── Provider / model toggles ───────────────────────────────────
        var providerSelect = document.getElementById('field-provider');
        var OPENAI_DEFAULT_MODEL = 'gpt-5.4-mini';
        var ANTHROPIC_DEFAULT_MODEL = 'claude-haiku-4-5';
        window.toggleOpenAIFields = function(providerValue) {
            var prov = (providerValue !== undefined && providerValue !== null && providerValue !== '')
                ? String(providerValue)
                : (providerSelect ? providerSelect.value : '');
            var isOpenAI = prov === 'openai';
            var pbuInput = document.getElementById('field-provider_base_url');
            if (pbuInput) {
                var dkey = isOpenAI ? 'data-default-openai' : 'data-default-anthropic';
                var dflt = pbuInput.getAttribute(dkey);
                if (dflt) pbuInput.value = dflt;
            }
            var modelInput = document.getElementById('field-model');
            if (modelInput) {
                var defaultModel = isOpenAI ? OPENAI_DEFAULT_MODEL : ANTHROPIC_DEFAULT_MODEL;
                modelInput.value = defaultModel;
                modelInput.placeholder = defaultModel;
            }
        };
        if (providerSelect) {
            providerSelect.addEventListener('change', function() { window.toggleOpenAIFields(); });
            window.toggleOpenAIFields();
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
        var _selectedTemplateUid = null;  // currently selected template unique id (full dataset file path)
        var _customSpecSelected = false;  // user selected a file from dataset browser
        var _templateLoading = false;     // true while a template's YAML/sections are being fetched
        var _editTplOriginalYaml = '';    // YAML content last loaded for the selected template; used for dirty-state

        // Dataset state (shared between spec browser and form submission)
        var _specDatasets = [];
        var _specCurrentDatasetId = '';
        var _specCurrentDatasetName = '';
        var _specCurrentSnapshotId = '';
        var _specCurrentDatasetPath = '';
        var _specCurrentPath = '';
        var _specBrowseAbort = null;
        var _browseSourceType = 'dataset';
        var _browseCodeIsGit = false;
        var _browseCodeRepoId = '';

        // Always use spacious layout: drawer history + inline preview
        var _layoutMode = 'B';

        function _applyLayoutMode() {
            var historyDetails = document.getElementById('history-details');
            if (historyDetails) historyDetails.style.display = 'none';
        }

        // ── Drawer open/close ──────────────────────────────────────────
        function openHistoryDrawer() {
            var overlay = document.getElementById('history-drawer-overlay');
            var drawer = document.getElementById('history-drawer');
            if (overlay) overlay.classList.add('open');
            if (drawer) drawer.classList.add('open');
            fetchJobHistory();
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
            var drawerOverlay = document.getElementById('history-drawer-overlay');
            if (drawerOverlay) drawerOverlay.addEventListener('click', closeHistoryDrawer);
            var landingBtn = document.getElementById('landing-history-btn');
            if (landingBtn) landingBtn.addEventListener('click', openHistoryDrawer);
        })();

        // ── Advanced options modal ─────────────────────────────────────
        function _loadCodePaths() {
            var input = document.getElementById('field-code_path');
            var list = document.getElementById('code-path-list');
            if (!input || !list) return;
            var pid = resolvedProjectId();
            if (!pid) return;
            fetch(_adUrl('api/code-paths') + '?projectId=' + encodeURIComponent(pid))
                .then(_checkResp).then(function(r) { return r.json(); })
                .then(function(data) {
                    if (!input.value) input.value = data.default || '';
                    list.innerHTML = '';
                    (data.paths || []).forEach(function(p) {
                        var opt = document.createElement('option');
                        opt.value = p;
                        list.appendChild(opt);
                    });
                })
                .catch(function() {});
        }

        (function() {
            var overlay = document.getElementById('adv-opts-overlay');
            var openBtn = document.getElementById('adv-opts-open-btn');
            var closeBtn = document.getElementById('adv-opts-close-btn');
            var doneBtn = document.getElementById('adv-opts-done-btn');
            function open() { if (overlay) overlay.classList.add('open'); _loadCodePaths(); }
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
            var browseMsg = document.getElementById('browse-selected-label');
            if (browseMsg) {
                browseMsg.textContent = 'Validating...';
            }

            var srcPath = _browseSelectedFile;
            var filename = String(srcPath || '').split('/').pop();
            var pid = resolvedProjectId();

            function _showGalleryOverlaySpinner() {
                var gallery = document.getElementById('template-gallery');
                if (!gallery) return;
                var overlay = document.getElementById('gallery-overlay-spinner');
                if (overlay) overlay.remove();
                overlay = document.createElement('div');
                overlay.id = 'gallery-overlay-spinner';
                overlay.style.position = 'absolute';
                overlay.style.inset = '0';
                overlay.style.display = 'flex';
                overlay.style.alignItems = 'center';
                overlay.style.justifyContent = 'center';
                overlay.style.background = 'rgba(255,255,255,0.65)';
                overlay.style.zIndex = '50';
                overlay.innerHTML =
                    '<span class="material-symbols-outlined" style="font-size:26px;margin-right:8px">hourglass_empty</span>'
                    + '<span style="font-weight:600">Refreshing templates...</span>';
                gallery.style.position = 'relative';
                gallery.appendChild(overlay);
            }

            function _hideGalleryOverlaySpinner() {
                var overlay = document.getElementById('gallery-overlay-spinner');
                if (overlay) overlay.remove();
            }

            var payload;
            if (_browseSourceType === 'gbp_git') {
                payload = {
                    sourceType: 'gbp_git',
                    sourceRepoId: _browseCodeRepoId,
                    sourcePath: srcPath,
                    filename: filename,
                };
            } else if (_browseSourceType === 'dfs_code') {
                payload = {
                    sourceType: 'dfs_code',
                    sourcePath: srcPath,
                    filename: filename,
                };
            } else {
                payload = {
                    sourceType: 'dataset',
                    sourceDatasetId: _specCurrentDatasetId,
                    sourceSnapshotId: _specCurrentSnapshotId,
                    sourcePath: srcPath,
                    filename: filename,
                };
            }

            fetch(_adUrl('api/add-spec-template') + (pid ? '?projectId=' + encodeURIComponent(pid) : ''), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            })
                .then(_checkResp)
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (!data || data.error) throw new Error((data && data.error) || 'Copy failed');
                    _showSpecConfirm(srcPath, 'browse');
                    closeBrowseModal();
                    _showGalleryOverlaySpinner();
                    return loadBuiltinTemplates();
                })
                .then(function() {
                    _hideGalleryOverlaySpinner();
                })
                .catch(function(err) {
                    _hideGalleryOverlaySpinner();
                    if (browseMsg) {
                        var msg = (err && err.message ? err.message : String(err));
                        if (typeof msg === 'string' && msg.toLowerCase().indexOf('missing required field:') === 0) {
                            browseMsg.textContent = msg;
                        } else {
                            browseMsg.textContent = 'Error: ' + msg;
                        }
                    }
                });
        }
        window.confirmBrowseSelection = confirmBrowseSelection;

        // ── Upload YAML spec ───────────────────────────────────────────
        var _uploadedSpecFile = null;

        function handleYamlUpload(input) {
            var file = input.files && input.files[0];
            if (!file) return;
            _uploadedSpecFile = file;
            input.value = '';

            var bar = document.getElementById('spec-confirm-bar');
            if (bar) {
                bar.innerHTML =
                    '<span class="spec-confirm-icon material-symbols-outlined">upload_file</span>' +
                    '<span class="spec-confirm-name">' + _esc(file.name) + '</span>' +
                    '<span class="spec-confirm-source">Uploading…</span>';
                bar.style.display = 'flex';
            }

            var pid = resolvedProjectId();
            var qs = pid ? ('?projectId=' + encodeURIComponent(pid)) : '';
            var fd = new FormData();
            fd.append('file', file, file.name);
            fetch(_adUrl('api/upload-spec-to-dataset') + qs, { method: 'POST', body: fd })
                .then(function(r) { return r.json().then(function(j) { return { ok: r.ok, body: j }; }); })
                .then(function(res) {
                    if (!res.ok || (res.body && res.body.error)) {
                        var msg = (res.body && res.body.error) || 'Upload failed';
                        if (bar) {
                            bar.innerHTML =
                                '<span class="spec-confirm-icon material-symbols-outlined">error</span>' +
                                '<span class="spec-confirm-name">' + _esc(file.name) + '</span>' +
                                '<span class="spec-confirm-source" style="color:var(--color-error)">' + _esc(msg) + '</span>' +
                                '<button type="button" class="spec-confirm-remove" onclick="removeUploadedSpec()" title="Remove">' +
                                '  <span class="material-symbols-outlined" style="font-size:15px">close</span>' +
                                '</button>';
                        }
                        _uploadedSpecFile = null;
                        return;
                    }
                    var path = res.body.path || '';
                    _customSpecSelected = true;
                    var specField = document.getElementById('field-spec_path');
                    if (specField) specField.value = path;
                    _showSpecConfirm(res.body.fileName || file.name, 'upload');
                    updateGenerateButton();
                    setTimeout(function() { try { loadBuiltinTemplates(); } catch(e) {} }, 500);
                })
                .catch(function(err) {
                    var msg = (err && err.message) ? err.message : String(err);
                    if (bar) {
                        bar.innerHTML =
                            '<span class="spec-confirm-icon material-symbols-outlined">error</span>' +
                            '<span class="spec-confirm-name">' + _esc(file.name) + '</span>' +
                            '<span class="spec-confirm-source" style="color:var(--color-error)">Upload failed: ' + _esc(msg) + '</span>' +
                            '<button type="button" class="spec-confirm-remove" onclick="removeUploadedSpec()" title="Remove">' +
                            '  <span class="material-symbols-outlined" style="font-size:15px">close</span>' +
                            '</button>';
                    }
                    _uploadedSpecFile = null;
                });
        }
        window.handleYamlUpload = handleYamlUpload;

        function removeUploadedSpec() {
            _uploadedSpecFile = null;
            _browseSelectedFile = null;
            _customSpecSelected = false;
            var specField = document.getElementById('field-spec_path');
            if (specField) specField.value = '';
            var bar = document.getElementById('spec-confirm-bar');
            if (bar) { bar.style.display = 'none'; bar.innerHTML = ''; }
            updateGenerateButton();
        }
        window.removeUploadedSpec = removeUploadedSpec;

        function _showSpecConfirm(filename, source) {
            var bar = document.getElementById('spec-confirm-bar');
            if (!bar) return;
            var icon = source === 'upload' ? 'upload_file' : 'description';
            bar.innerHTML =
                '<span class="spec-confirm-icon material-symbols-outlined">' + icon + '</span>' +
                '<span class="spec-confirm-name">' + filename + '</span>' +
                '<span class="spec-confirm-source">' + (source === 'upload' ? 'Uploaded' : (_browseSourceType === 'dataset' ? 'From dataset' : 'From code')) + '</span>' +
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
            var hasTemplate = !!_selectedTemplateUid;
            var hasCustomSpec = _customSpecSelected;
            var canGenerate = hasTemplate || hasCustomSpec;
            btn.disabled = !canGenerate;

        }

        // ── Template gallery ───────────────────────────────────────────
        function loadBuiltinTemplates() {
            var pid = resolvedProjectId();
            var url = _adUrl('api/built-in-templates');
            if (pid) url += '?projectId=' + encodeURIComponent(pid);
            return fetch(url)
                .then(_checkResp).then(function(r) { return r.json(); })
                .then(function(templates) {
                    if (!Array.isArray(templates)) throw new Error('bad response');
                    _builtinTemplates = templates;
                    renderTemplateGallery(templates);
                    var sel = _selectedTemplateUid;
                    if (sel) {
                        var still = false;
                        for (var k = 0; k < templates.length; k++) {
                            if (templates[k].uid === sel || templates[k].template_file === sel) { still = true; break; }
                        }
                        if (still) selectTemplate(sel);
                    }
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

        var _previewEmptyDefaultHtml = null;
        function _rememberPreviewDefaultHtml() {
            var el = document.getElementById('template-preview-empty');
            if (el && _previewEmptyDefaultHtml === null) {
                _previewEmptyDefaultHtml = el.innerHTML;
            }
        }
        function resetTemplateYamlPreview() {
            var panel = document.getElementById('template-preview-panel');
            if (panel && _previewEmptyDefaultHtml !== null) {
                panel.innerHTML = '<div class="preview-empty-state" id="template-preview-empty">'
                    + _previewEmptyDefaultHtml + '</div>';
            }
            var editArea = document.getElementById('edit-template-yaml');
            if (editArea) editArea.value = '';
            _editTplOriginalYaml = '';
            var editSection = document.getElementById('edit-tpl-section');
            if (editSection) editSection.removeAttribute('data-uid');
            _setEditTplStatus('', '');
            _updateEditTplButtons();
        }
        function _renderTemplatePreviewSections(tpl, sections, perModelSections) {
            var panel = document.getElementById('template-preview-panel');
            if (!panel) return;
            sections = sections || [];
            var perModelSet = {};
            (perModelSections || []).forEach(function(s) { perModelSet[s] = true; });
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
                + '<div class="preview-title">' + _esc(tpl.name || '') + '</div>'
                + '<div class="preview-description">' + _esc(tpl.description || '') + '</div>'
                + '</div>'
                + '<div class="preview-sections">' + sectionsHtml + '</div>';
        }

        function _setEditTplStatus(text, kind) {
            var el = document.getElementById('edit-tpl-status');
            if (!el) return;
            el.textContent = text || '';
            el.classList.remove('error', 'success');
            if (kind === 'error' || kind === 'success') el.classList.add(kind);
        }

        function _editTplFilename() {
            var sec = document.getElementById('edit-tpl-section');
            var uid = sec ? (sec.getAttribute('data-uid') || '') : '';
            if (!uid) return '';
            return uid.replace(/\\/g, '/').split('/').pop();
        }

        function _updateEditTplButtons() {
            var saveBtn = document.getElementById('edit-tpl-save-btn');
            var revertBtn = document.getElementById('edit-tpl-revert-btn');
            var editArea = document.getElementById('edit-template-yaml');
            var hasTemplate = !!_editTplFilename();
            var current = editArea ? (editArea.value || '') : '';
            var hasContent = current.length > 0;
            var dirty = current !== _editTplOriginalYaml;
            if (saveBtn) saveBtn.disabled = !(hasTemplate && hasContent && dirty);
            if (revertBtn) revertBtn.disabled = !(hasTemplate && dirty);
        }

        function _editTplSave() {
            var saveBtn = document.getElementById('edit-tpl-save-btn');
            var editArea = document.getElementById('edit-template-yaml');
            if (!editArea) return;
            var filename = _editTplFilename();
            if (!filename) return;
            var content = editArea.value || '';
            if (!content) return;

            _setEditTplStatus('Saving...', '');
            if (saveBtn) saveBtn.disabled = true;
            var revertBtn = document.getElementById('edit-tpl-revert-btn');
            if (revertBtn) revertBtn.disabled = true;

            var pid = resolvedProjectId();
            var qs = pid ? ('?projectId=' + encodeURIComponent(pid)) : '';
            var blob = new Blob([content], { type: 'text/yaml' });
            var fd = new FormData();
            fd.append('file', blob, filename);
            fd.append('filename', filename);

            fetch(_adUrl('api/upload-spec-to-dataset') + qs, { method: 'POST', body: fd })
                .then(function(r) { return r.json().then(function(j) { return { ok: r.ok, body: j }; }); })
                .then(function(res) {
                    if (!res.ok || (res.body && res.body.error)) {
                        var msg = (res.body && res.body.error) || 'Save failed';
                        _setEditTplStatus(msg, 'error');
                        _updateEditTplButtons();
                        return;
                    }
                    _editTplOriginalYaml = content;
                    _setEditTplStatus('Saved.', 'success');
                    _updateEditTplButtons();
                    // Refresh gallery so card metadata stays in sync if it changed.
                    try { loadBuiltinTemplates(); } catch (e) {}
                })
                .catch(function(err) {
                    _setEditTplStatus('Save failed: ' + (err && err.message ? err.message : String(err)), 'error');
                    _updateEditTplButtons();
                });
        }

        function _editTplRevert() {
            var editArea = document.getElementById('edit-template-yaml');
            if (!editArea) return;
            editArea.value = _editTplOriginalYaml || '';
            _setEditTplStatus('', '');
            _updateEditTplButtons();
        }

        function wireEditTemplateActions() {
            var saveBtn = document.getElementById('edit-tpl-save-btn');
            var revertBtn = document.getElementById('edit-tpl-revert-btn');
            var editArea = document.getElementById('edit-template-yaml');
            if (saveBtn) saveBtn.addEventListener('click', _editTplSave);
            if (revertBtn) revertBtn.addEventListener('click', _editTplRevert);
            if (editArea) editArea.addEventListener('input', _updateEditTplButtons);
            _updateEditTplButtons();
        }
        wireEditTemplateActions();

        function wireEditTemplateMaximize() {
            var btn = document.getElementById('edit-tpl-maximize-btn');
            if (!btn) return;
            btn.addEventListener('click', function() {
                var card = btn.closest('.preview-card');
                if (!card) return;
                var maximized = card.classList.toggle('edit-maximized');
                btn.setAttribute('aria-pressed', maximized ? 'true' : 'false');
                btn.setAttribute('title', maximized ? 'Restore editor' : 'Maximize editor');
                btn.setAttribute('aria-label', maximized ? 'Restore editor' : 'Maximize editor');
                var icon = btn.querySelector('.edit-tpl-maximize-icon');
                if (icon) icon.textContent = maximized ? 'close_fullscreen' : 'open_in_full';
            });
        }
        wireEditTemplateMaximize();

        function _setTemplateLoading(loading) {
            _templateLoading = !!loading;
            var cards = document.querySelectorAll('.template-card');
            for (var i = 0; i < cards.length; i++) {
                cards[i].classList.toggle('loading', !!loading);
            }
            var overlay = document.getElementById('preview-card-loading');
            if (overlay) overlay.classList.toggle('active', !!loading);
        }

        function loadYamlTemplatePreview(tpl) {
            var panel = document.getElementById('template-preview-panel');
            if (!panel) return;
            _setTemplateLoading(true);
            // Stamp the template uid as data-uid on the editor section + preview empty,
            // mirroring the data-uid attribute on .template-card. Source of truth.
            var uid = tpl.uid || tpl.template_path || tpl.template_file || '';
            var editSection = document.getElementById('edit-tpl-section');
            if (editSection) editSection.setAttribute('data-uid', uid);
            var emptyEl = document.getElementById('template-preview-empty');
            if (emptyEl) emptyEl.setAttribute('data-uid', uid);

            var pid = resolvedProjectId();
            var tplFile = encodeURIComponent(tpl.template_file || '');
            var pidQs = pid ? ('&projectId=' + encodeURIComponent(pid)) : '';
            var yamlUrl = _adUrl('api/built-in-template') + '?template_file=' + tplFile + pidQs;
            var sectionsUrl = _adUrl('api/built-in-template-sections') + '?template_file=' + tplFile + pidQs;

            var yamlPromise = fetch(yamlUrl)
                .then(_checkResp)
                .then(function(r) { return r.text(); })
                .then(function(text) {
                    var editArea = document.getElementById('edit-template-yaml');
                    if (editArea) {
                        editArea.value = text || '';
                        _editTplOriginalYaml = text || '';
                    }
                    _updateEditTplButtons();
                    _setEditTplStatus('', '');
                })
                .catch(function() {
                    var editArea = document.getElementById('edit-template-yaml');
                    if (editArea) editArea.value = '';
                    _editTplOriginalYaml = '';
                    _updateEditTplButtons();
                });

            var sectionsPromise = fetch(sectionsUrl)
                .then(_checkResp)
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    _renderTemplatePreviewSections(tpl, (data && data.sections) || [], (data && data.per_model_sections) || []);
                })
                .catch(function() {
                    var p = document.getElementById('template-preview-panel');
                    if (p) {
                        p.innerHTML = '<div class="preview-empty-state" id="template-preview-empty">'
                            + '<span class="material-symbols-outlined preview-empty-icon">error</span>'
                            + '<span class="preview-empty-text">Could not load template</span>'
                            + '</div>';
                    }
                });

            Promise.all([yamlPromise, sectionsPromise]).then(function() {
                _setTemplateLoading(false);
            });
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
                var fn = t.template_file || '';
                var n = typeof t.section_count === 'number' ? t.section_count : parseInt(t.section_count, 10);
                if (isNaN(n) || n < 0) n = 0;
                var badgeText = n ? (String(n) + ' sections') : '';
                var uid = t.uid || '';
                if (!uid) uid = fn || t.slug || '';
                html += '<div class="template-card" data-uid="' + _esc(uid) + '" tabindex="0" role="button" aria-pressed="false">'
                    + '<div class="template-card-header">'
                    + '<span class="template-card-name">' + _esc(t.name) + '</span>'
                    + '<span class="material-symbols-outlined template-card-check">check_circle</span>'
                    + '</div>'
                    + '<p class="template-card-desc">' + _esc(t.description) + '</p>'
                    + '<div class="template-card-meta">'
                    + '<span class="template-card-badge">' + _esc(badgeText || fn) + '</span>'
                    + '</div>'
                    + '</div>';
            }
            gallery.innerHTML = html;

            // Wire click/keyboard handlers
            var cards = gallery.querySelectorAll('.template-card');
            for (var j = 0; j < cards.length; j++) {
                (function(card) {
                    card.addEventListener('click', function() {
                        selectTemplate(card.getAttribute('data-uid'));
                    });
                    card.addEventListener('keydown', function(e) {
                        if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            selectTemplate(card.getAttribute('data-uid'));
                        }
                    });
                })(cards[j]);
            }
        }

        function selectTemplate(uid) {
            if (_templateLoading) return;
            _selectedTemplateUid = uid;
            _customSpecSelected = false;

            // Update card UI
            var cards = document.querySelectorAll('.template-card');
            for (var i = 0; i < cards.length; i++) {
                var isSelected = cards[i].getAttribute('data-uid') === uid;
                cards[i].classList.toggle('selected', isSelected);
                cards[i].setAttribute('aria-pressed', isSelected ? 'true' : 'false');
            }

            var tpl = null;
            for (var j = 0; j < _builtinTemplates.length; j++) {
                if (_builtinTemplates[j].uid === uid || _builtinTemplates[j].template_file === uid) { tpl = _builtinTemplates[j]; break; }
            }
            if (tpl) loadYamlTemplatePreview(tpl);

            updateGenerateButton();
        }

        // ── Dataset auto-resolution ────────────────────────────────────
        // The project's autodoc dataset is resolved automatically from the
        // project ID — no user selection required.
        var specFileList = document.getElementById('spec-file-list');
        var specBreadcrumb = document.getElementById('spec-breadcrumb');
        var specMachineUpload = document.getElementById('spec-machine-upload');
        var specUploadStatus = document.getElementById('spec-upload-status');
        var specPathField = document.getElementById('field-spec_path');

        // Browse modal dataset selection (separate UI from the auto-resolved dataset)
        var browseDatasetSelect = document.getElementById('browse-dataset-select');

        function browseModalApplyDataset(d) {
            if (!d) return;
            _specCurrentDatasetId = d.id || '';
            _specCurrentDatasetName = d.name || '';
            _specCurrentSnapshotId = d.rwSnapshotId || '';
            _specCurrentDatasetPath = d.datasetPath || '';
            _specCurrentPath = '';
            if (specPathField && !_selectedTemplateUid) specPathField.value = '';
            if (_specCurrentDatasetId) browseFiles('');
            updateGenerateButton();
        }

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
            if (specPathField && !_selectedTemplateUid) specPathField.value = '';
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
                    // Do not auto-apply any dataset for the spec browser flow.
                    // The spec file browser should only show content after the user
                    // explicitly selects a dataset in the browse modal.
                    fetchJobHistory();
                })
                .catch(function() { /* silently ignore — dataset is optional for template-based flow */ });
        }

        loadDatasets();

        function loadBrowseModalDatasets() {
            if (!browseDatasetSelect) return;
            var pid = resolvedProjectId();
            if (!pid) return;

            var codeRootPromise = fetch(_adUrl('api/code-root') + '?projectId=' + encodeURIComponent(pid))
                .then(_checkResp).then(function(r) { return r.json(); })
                .catch(function() { return null; });
            var datasetsPromise = fetch(_adUrl('api/datasets') + '?projectId=' + encodeURIComponent(pid))
                .then(_checkResp).then(function(r) { return r.json(); })
                .catch(function() { return []; });

            Promise.all([codeRootPromise, datasetsPromise]).then(function(results) {
                var codeInfo = results[0];
                var datasets = results[1] || [];
                var html = '';

                if (codeInfo && !codeInfo.error) {
                    html += '<option value="__code__" data-type="code" data-is-git="' + (codeInfo.isGit ? 'true' : 'false') + '" data-repo-id="' + (codeInfo.repoId || '') + '">'
                        + 'Source code' + '</option>';
                }

                for (var i = 0; i < datasets.length; i++) {
                    if (datasets[i] && datasets[i].name === 'autodoc') continue;
                    var ds = datasets[i] || {};
                    html += '<option value="' + (ds.id || '') + '" data-type="dataset" data-name="' + (ds.name || '') + '" data-snapshot="' + (ds.rwSnapshotId || '') + '" data-path="' + (ds.datasetPath || '') + '">'
                        + (ds.name || ds.id || '') + '</option>';
                }

                if (!html) {
                    browseDatasetSelect.innerHTML = '<option value="" disabled selected>No sources found</option>';
                    return;
                }
                browseDatasetSelect.innerHTML = html;
                var firstOpt = browseDatasetSelect.options[0];
                if (firstOpt) {
                    browseDatasetSelect.value = firstOpt.value || '';
                    onBrowseModalDatasetChange();
                }
            });
        }

        function onBrowseModalDatasetChange() {
            if (!browseDatasetSelect) return;
            var opt = browseDatasetSelect.options[browseDatasetSelect.selectedIndex];
            if (!opt) return;
            var srcType = opt.getAttribute('data-type') || 'dataset';

            if (srcType === 'code') {
                _browseSourceType = opt.getAttribute('data-is-git') === 'true' ? 'gbp_git' : 'dfs_code';
                _browseCodeIsGit = _browseSourceType === 'gbp_git';
                _browseCodeRepoId = opt.getAttribute('data-repo-id') || '';
                _specCurrentDatasetId = '';
                _specCurrentSnapshotId = '';
                _specCurrentPath = '';
                browseFiles('');
            } else {
                _browseSourceType = 'dataset';
                _browseCodeIsGit = false;
                _browseCodeRepoId = '';
                var dsId = browseDatasetSelect.value || '';
                if (!dsId) return;
                var ds = {
                    id: dsId,
                    name: opt.getAttribute('data-name') || '',
                    rwSnapshotId: opt.getAttribute('data-snapshot') || '',
                    datasetPath: opt.getAttribute('data-path') || '',
                };
                browseModalApplyDataset(ds);
            }
        }

        if (browseDatasetSelect) {
            browseDatasetSelect.addEventListener('change', onBrowseModalDatasetChange);
            loadBrowseModalDatasets();
        }

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

            var isCode = _browseSourceType === 'gbp_git' || _browseSourceType === 'dfs_code';
            if (!isCode && !_specCurrentDatasetId) {
                specFileList.innerHTML = '<div class="spec-file-empty"><span class="spec-file-list-empty">Select a source first</span></div>';
                return Promise.resolve();
            }

            renderBreadcrumb(path);
            if (_specBrowseAbort) _specBrowseAbort.abort();
            var ctrl = _specBrowseAbort = new AbortController();
            specFileList.classList.add('spec-file-list-pending');
            specFileList.innerHTML = '<div class="spec-file-empty"><span class="spec-file-list-empty">Loading…</span></div>';

            var fetchUrl;
            if (isCode) {
                var pid = resolvedProjectId();
                var qparts = [];
                if (pid) qparts.push('projectId=' + encodeURIComponent(pid));
                qparts.push('isGit=' + (_browseCodeIsGit ? 'true' : 'false'));
                if (_browseCodeRepoId) qparts.push('repoId=' + encodeURIComponent(_browseCodeRepoId));
                if (path) qparts.push('path=' + encodeURIComponent(path));
                fetchUrl = _adUrl('api/code-files') + '?' + qparts.join('&');
            } else {
                fetchUrl = _adUrl('api/dataset-files') + queryApiDatasetFiles(path);
            }

            return fetch(fetchUrl, { signal: ctrl.signal })
                .then(_checkResp).then(function(r) { return r.json(); })
                .then(function(files) {
                    if (!Array.isArray(files)) {
                        specFileList.innerHTML = '<div class="spec-file-empty"><span class="spec-file-list-empty">'
                            + (files && files.error ? 'Error: ' + files.error : 'Unexpected response') + '</span></div>';
                        return;
                    }
                    if (isCode) {
                        files = files.filter(function(f) {
                            if (f.isDirectory) return true;
                            var n = (f.fileName || '').toLowerCase();
                            return n.endsWith('.yaml') || n.endsWith('.yml');
                        });
                    }
                    var html = '';
                    var parentPath = specParentPath(path);
                    if (parentPath !== null) {
                        html += '<div class="spec-file-item spec-file-parent" data-path="' + parentPath + '" data-dir="true" data-name=".." data-parent="true">'
                            + '<span class="spec-file-icon">\ud83d\udcc1</span>'
                            + '<span class="spec-file-name">..</span>'
                            + '</div>';
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
                        var fullPath = path ? path + '/' + f.fileName : f.fileName;
                        html += '<div class="spec-file-item" data-path="' + fullPath + '" data-dir="' + f.isDirectory + '" data-name="' + f.fileName + '">'
                            + '<span class="spec-file-icon">' + icon + '</span>'
                            + '<span class="spec-file-name">' + f.fileName + '</span>'
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
                _browseSelectedFile = null;
                var browseLabel = document.getElementById('browse-selected-label');
                if (browseLabel) browseLabel.textContent = '';
                var btn = document.getElementById('browse-confirm-btn');
                if (btn) btn.disabled = true;
                browseFiles(path);
            } else {
                var items = specFileList ? specFileList.querySelectorAll('.spec-file-item') : [];
                for (var i = 0; i < items.length; i++) items[i].classList.remove('selected');
                el.classList.add('selected');
                // Reuse the modal selection variable so the "Select" button enables.
                _browseSelectedFile = path;
                var browseLabel = document.getElementById('browse-selected-label');
                if (browseLabel) browseLabel.textContent = path;
                var btn = document.getElementById('browse-confirm-btn');
                if (btn) btn.disabled = false;

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
            _selectedTemplateUid = null;
            _customSpecSelected = true;
            resetTemplateYamlPreview();
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
                        return browseFiles(_specCurrentPath).then(function() { return loadBuiltinTemplates(); });
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

        function _formatSubmitted(iso) {
            if (!iso) return '\u2014';
            // Backend serializes as UTC without a 'Z' suffix; Date treats no-suffix ISO as local.
            // Append 'Z' so it's parsed as UTC, then format in the browser's local TZ.
            var raw = String(iso);
            var d = new Date(/[zZ]|[+-]\d{2}:?\d{2}$/.test(raw) ? raw : raw + 'Z');
            if (isNaN(d.getTime())) return iso;
            var pad = function(n) { return n < 10 ? '0' + n : '' + n; };
            return pad(d.getMonth() + 1) + '/' + pad(d.getDate()) + '/' + pad(d.getFullYear() % 100)
                + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
        }

        function _jobRow(j) {
            var status = j.status || 'queued';
            var statusCls = 'history-status history-status-' + status;
            var submitted = _formatSubmitted(j.submitted_at);
            var runId = j.domino_run_id || '';
            var jobCell = j.job_url
                ? '<td><a href="' + _esc(j.job_url) + '" target="_blank" rel="noopener">View \u2192</a></td>'
                : '<td>\u2014</td>';
            var isActive = _ACTIVE_STATUSES[status];
            var docCell;
            if (status === 'succeeded' && j.document_url) {
                var openLink = '<a href="' + _esc(j.document_url) + '" target="_blank" rel="noopener">Open \u2192</a>';
                var previewLink = runId
                    ? '<a href="#" class="history-preview-link" data-run-id="' + _esc(runId) + '">Preview</a>'
                    : '';
                docCell = '<td class="history-documents-cell">' + openLink + (previewLink ? '<br>' + previewLink : '') + '</td>';
            } else if (isActive) {
                docCell = '<td class="history-pending-cell">Pending\u2026</td>';
            } else {
                docCell = '<td>\u2014</td>';
            }
            var rowAttrs = runId ? ' data-run-id="' + _esc(runId) + '"' : '';
            return '<tr' + rowAttrs + '>'
                + '<td><span class="' + statusCls + '">' + _esc(status.toUpperCase()) + '</span></td>'
                + '<td class="history-submitted-cell">' + _esc(submitted) + '</td>'
                + docCell
                + jobCell
                + '</tr>';
        }

        function _tableHtml(jobs) {
            var header = '<thead><tr><th>Status</th><th>Submitted</th><th>Documents</th><th>Job</th></tr></thead>';
            var rows = jobs.map(function(j) { return _jobRow(j); }).join('');
            return '<table class="history-table">' + header + '<tbody>' + rows + '</tbody></table>';
        }

        var _lastResultsPanelKey = null;

        function renderResultsPanel(jobs) {
            var panel = document.getElementById('results-panel');
            if (!panel) return;
            if (!jobs || !jobs.length) return;

            var latestJob = jobs[0];
            var status = latestJob.status || 'queued';

            var panelKey = (latestJob.job_id || latestJob.domino_run_id || '') + '|' + status;
            var isTerminal = (status === 'succeeded' || status === 'failed' || status === 'cancelled');
            if (isTerminal && panelKey === _lastResultsPanelKey) {
                return;
            }
            _lastResultsPanelKey = panelKey;

            var html = '<div class="results-job-card">';

            // Header row
            html += '<div class="results-job-header">';
            html += '<div class="results-job-info">';
            if (_selectedTemplateUid) {
                var tplName = '';
                for (var i = 0; i < _builtinTemplates.length; i++) {
                    if (_builtinTemplates[i].uid === _selectedTemplateUid || _builtinTemplates[i].template_file === _selectedTemplateUid) { tplName = _builtinTemplates[i].name; break; }
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
                var autodocLink = latestJob.document_url
                    ? '<a href="' + _esc(latestJob.document_url) + '" target="_blank" rel="noopener" class="success-open-btn">'
                        + '<span class="material-symbols-outlined" style="font-size:15px">folder_open</span>Open AutoDoc file</a>'
                    : '';
                html += '<div class="results-success-banner">'
                    + '<span class="material-symbols-outlined results-success-icon">check_circle</span>'
                    + '<div class="results-success-text">'
                    + '<div class="results-success-headline">Documentation generated successfully</div>'
                    + '</div>'
                    + (autodocLink ? autodocLink : '')
                    + '</div>';
                if (latestJob.domino_run_id) {
                    html += '<div class="doc-preview-wrap" id="doc-preview-wrap">'
                        + '<div class="doc-preview-loading" id="doc-preview-loading">'
                        + '<span class="material-symbols-outlined doc-preview-spin">autorenew</span>'
                        + '<span>Loading preview…</span>'
                        + '</div>'
                        + '<div class="doc-preview-content" id="doc-preview-content" style="display:none"></div>'
                        + '<div class="doc-preview-error" id="doc-preview-error" style="display:none"></div>'
                        + '</div>';
                }
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

            if (status === 'succeeded' && latestJob.domino_run_id) {
                _loadDocPreview(latestJob.domino_run_id);
            }

            // Start or stop the progress label cycle
            if (status === 'running' || status === 'submitted' || status === 'pending') {
                _startProgressCycle();
            } else {
                _stopProgressCycle();
            }
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
                el.querySelectorAll('.history-preview-link').forEach(function(link) {
                    link.addEventListener('click', function(e) {
                        e.preventDefault();
                        var runId = link.getAttribute('data-run-id');
                        if (runId) {
                            closeHistoryDrawer();
                            _openLandingDocPreview(runId);
                        }
                    });
                });
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
        var _docPreviewRunId = null;
        var _docPreviewTimer = null;

        function _loadDocPreview(runId) {
            _docPreviewRunId = runId;
            if (_docPreviewTimer) { clearTimeout(_docPreviewTimer); _docPreviewTimer = null; }
            var pid = resolvedProjectId();
            fetch(_adUrl('api/preview-doc') + '?projectId=' + encodeURIComponent(pid) + '&runId=' + encodeURIComponent(runId))
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    var wrap = document.getElementById('doc-preview-wrap');
                    if (!wrap || _docPreviewRunId !== runId) return;
                    var loading = document.getElementById('doc-preview-loading');
                    var content = document.getElementById('doc-preview-content');
                    var err = document.getElementById('doc-preview-error');
                    if (data.ready && data.html) {
                        if (loading) loading.style.display = 'none';
                        if (content) { content.innerHTML = data.html; content.style.display = ''; }
                    } else if (!data.ready) {
                        _docPreviewTimer = setTimeout(function() { _loadDocPreview(runId); }, 3000);
                    } else {
                        if (loading) loading.style.display = 'none';
                        if (err) { err.textContent = data.error || 'Preview unavailable.'; err.style.display = ''; }
                    }
                })
                .catch(function() {
                    _docPreviewTimer = setTimeout(function() { _loadDocPreview(runId); }, 5000);
                });
        }

        var _landingPreviewOriginalHtml = null;
        var _landingPreviewOriginalEditYaml = null;

        function _openLandingDocPreview(runId) {
            var card = document.querySelector('.preview-card');
            if (!card) return;
            _landingPreviewOriginalHtml = card.innerHTML;
            var _editAreaSnap = document.getElementById('edit-template-yaml');
            _landingPreviewOriginalEditYaml = _editAreaSnap ? _editAreaSnap.value : null;
            card.innerHTML = '<div class="landing-doc-preview">'
                + '<div class="landing-doc-preview-header">'
                + '<span class="landing-doc-preview-title">Document Preview</span>'
                + '<button type="button" class="landing-doc-preview-close" id="landing-doc-preview-close">'
                + '<span class="material-symbols-outlined">close</span></button>'
                + '</div>'
                + '<div class="landing-doc-preview-body" id="landing-doc-preview-body">'
                + '<div class="doc-preview-loading">'
                + '<span class="material-symbols-outlined doc-preview-spin">autorenew</span>'
                + '<span>Loading preview…</span>'
                + '</div>'
                + '</div>'
                + '</div>';
            var closeBtn = document.getElementById('landing-doc-preview-close');
            if (closeBtn) closeBtn.addEventListener('click', _closeLandingDocPreview);
            var pid = resolvedProjectId();
            fetch(_adUrl('api/preview-doc') + '?projectId=' + encodeURIComponent(pid) + '&runId=' + encodeURIComponent(runId))
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    var body = document.getElementById('landing-doc-preview-body');
                    if (!body) return;
                    if (data.ready && data.html) {
                        body.innerHTML = '<div class="doc-preview-content">' + data.html + '</div>';
                    } else {
                        body.innerHTML = '<div class="doc-preview-error">'
                            + (data.error || (data.ready === false ? 'Document not ready yet.' : 'Preview unavailable.'))
                            + '</div>';
                    }
                })
                .catch(function() {
                    var body = document.getElementById('landing-doc-preview-body');
                    if (body) body.innerHTML = '<div class="doc-preview-error">Failed to load preview.</div>';
                });
        }

        function _closeLandingDocPreview() {
            var card = document.querySelector('.preview-card');
            if (!card || _landingPreviewOriginalHtml === null) return;
            card.innerHTML = _landingPreviewOriginalHtml;
            _landingPreviewOriginalHtml = null;
            if (_landingPreviewOriginalEditYaml !== null) {
                var editArea = document.getElementById('edit-template-yaml');
                if (editArea) editArea.value = _landingPreviewOriginalEditYaml;
                _landingPreviewOriginalEditYaml = null;
            }
            wireEditTemplateActions();
            wireEditTemplateMaximize();
            var landingBtn = document.getElementById('landing-history-btn');
            if (landingBtn) landingBtn.addEventListener('click', openHistoryDrawer);
        }

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

        var generateBtn = document.getElementById('generate-btn');
        if (generateBtn) {
            generateBtn.addEventListener('click', function() {
                hideWizardError();
                if (generateBtn) generateBtn.disabled = true;

                function val(id) {
                    var el = document.getElementById(id);
                    return el ? String(el.value || '').trim() : '';
                }
                function chk(id) {
                    var el = document.getElementById(id);
                    return !!(el && el.checked);
                }
                function submitJob(specPath) {
                    if (specPathField) specPathField.value = specPath;

                    var jsonPayload = {
                        spec_path: specPath,
                        provider: val('field-provider'),
                        model: val('field-model'),
                        notebook: true,
                        notebook_path: '',
                        notebook_from_cache: false,
                        filtered_experiment_names: val('filter-experiment-names'),
                        filtered_model_names: val('filter-model-names'),
                        latest_only: chk('filter-latest-only'),
                        hardware_tier: val('field-hardware_tier'),
                        provider_base_url: val('field-provider_base_url'),
                        code_path: val('field-code_path'),
                    };

                    var pid = resolvedProjectId();
                    showStep2();
                    var panel = document.getElementById('results-panel');
                    if (panel) {
                        panel.innerHTML = '<div class="results-submitting">'
                            + '<span class="material-symbols-outlined results-submitting-icon">rocket_launch</span>'
                            + '<span class="results-submitting-text">Submitting job\u2026</span>'
                            + '</div>';
                    }

                    var qs = pid ? ('?projectId=' + encodeURIComponent(pid)) : '';
                    fetch(_adUrl('run') + qs, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(jsonPayload),
                    })
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
                            if (generateBtn) generateBtn.disabled = false;
                            updateGenerateButton();
                        });
                }

                if (_selectedTemplateUid) {
                    var tpl = null;
                    for (var i = 0; i < _builtinTemplates.length; i++) {
                        if (_builtinTemplates[i].uid === _selectedTemplateUid || _builtinTemplates[i].template_file === _selectedTemplateUid) { tpl = _builtinTemplates[i]; break; }
                    }
                    if (!tpl) {
                        showWizardError('Selected template not found. Please refresh the page.');
                        if (generateBtn) generateBtn.disabled = false;
                        updateGenerateButton();
                        return;
                    }
                    var specPath = tpl.template_path || tpl.uid || '';
                    if (!specPath) {
                        showWizardError('Selected template has no template path.');
                        if (generateBtn) generateBtn.disabled = false;
                        updateGenerateButton();
                        return;
                    }
                    submitJob(specPath);
                } else if (_customSpecSelected && specPathField && specPathField.value.trim()) {
                    submitJob(specPathField.value.trim());
                } else {
                    showWizardError('Please select a template or a custom spec file.');
                    if (generateBtn) generateBtn.disabled = false;
                    updateGenerateButton();
                }
            });
        }

        // ── Init ───────────────────────────────────────────────────────
        _rememberPreviewDefaultHtml();
        loadBuiltinTemplates();
        updateGenerateButton();

    }); // end DOMContentLoaded
"""
