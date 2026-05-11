"""All JavaScript code for the Stitch UI."""

from __future__ import annotations


MAIN_DOM_JS = r"""
    // ── Shared fetch helper: check response status before parsing ──
    function _checkResp(r) {
        if (!r.ok) throw new Error('Server error (' + r.status + ')');
        return r;
    }

    // ── URL prefixing for Domino app proxy ──
    // Domino serves this app under /apps/<id>/ (or /apps-internal/<id>/).
    // The served page URL has no trailing slash, so relative URLs like
    // "api/datasets" resolve to "/apps/api/datasets" and break. We derive
    // the prefix from window.location.pathname and prepend it ourselves.
    var _AD_APP_BASE = (function() {
        var m = (window.location.pathname || '').match(/^(\/apps(?:-internal)?\/[^/]+)/i);
        return m ? m[1] + '/' : '';
    })();
    function _adUrl(rel) {
        if (!_AD_APP_BASE) return rel;
        return _AD_APP_BASE + (rel.charAt(0) === '/' ? rel.slice(1) : rel);
    }
    // Rewrite any element with data-app-rel="path" to use the full prefix.
    // Applies to <a href> and <form action>.
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

        (function() {
            var tip = document.createElement('div');
            tip.id = 'studio-info-tooltip';
            tip.setAttribute('role', 'tooltip');
            document.body.appendChild(tip);
            var active = null;
            function hide() {
                tip.classList.remove('visible');
                tip.textContent = '';
                active = null;
            }
            function position() {
                if (!active || !tip.classList.contains('visible')) return;
                var r = active.getBoundingClientRect();
                var gap = 6;
                tip.style.visibility = 'hidden';
                tip.style.display = 'block';
                var tw = tip.offsetWidth;
                var th = tip.offsetHeight;
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

        // ── Ensure projectId is on the page URL (reload if we only have hash / postMessage) ──
        (function() {
            function setProjectId(pid) {
                if (!pid) return;
                try {
                    var u = new URL(window.location.href);
                    if (u.searchParams.get('projectId') === pid) return;
                    u.searchParams.set('projectId', pid);
                    window.location.replace(u.toString());
                } catch (e) { /* ignore */ }
            }
            var pid = null;
            pid = new URLSearchParams(window.location.search).get('projectId');
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
                } catch(e) { /* cross-origin */ }
            }
            if (pid) {
                setProjectId(pid);
            }
            window.addEventListener('message', function(e) {
                if (e.data && typeof e.data === 'object' && e.data.projectId) {
                    setProjectId(e.data.projectId);
                }
            });
        })();

        // ── Language detection ────────────────────────────────────────────
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

        const providerSelect    = document.getElementById('field-provider');
        const modelNameField    = document.getElementById('model-name-field');

        // ── Dataset spec browser (Domino mode) ───────────────────────────
        var specDatasetSelect = document.getElementById('spec-dataset-select');
        var specFileList = document.getElementById('spec-file-list');
        var specBreadcrumb = document.getElementById('spec-breadcrumb');
        var specSelectedIndicator = document.getElementById('spec-selected-indicator');
        var specMachineUpload = document.getElementById('spec-machine-upload');
        var specUploadStatus = document.getElementById('spec-upload-status');
        var specPathField = document.getElementById('field-spec_path');

        // State
        var _specDatasets = [];
        var _specCurrentDatasetId = '';
        var _specCurrentDatasetName = '';
        var _specCurrentSnapshotId = '';
        var _specCurrentDatasetPath = '';
        var _specCurrentPath = '';
        var _specAutoDocSpecsId = '';
        var _specBrowseAbort = null;

        function resolvedProjectId() {
            var params = new URLSearchParams(window.location.search);
            return params.get('projectId') || params.get('project_id') || '';
        }

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

        function queryApiDatasets() {
            var pid = resolvedProjectId();
            return pid ? ('?projectId=' + encodeURIComponent(pid)) : '';
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
            return parts.length ? ('?' + parts.join('&')) : '';
        }

        function loadDatasets() {
            if (!specDatasetSelect) return;
            var pid = resolvedProjectId();
            if (!pid) {
                specDatasetSelect.innerHTML = '<option value="">Set a project ID first</option>';
                return;
            }
            console.log('[spec-browser] Loading writable datasets...');
            fetch(_adUrl('api/datasets') + '?projectId=' + encodeURIComponent(pid))
                .then(_checkResp).then(function(r) { return r.json(); })
                .then(function(datasets) {
                    if (datasets.error) {
                        console.error('[spec-browser] Error loading datasets:', datasets.error);
                        specDatasetSelect.innerHTML = '<option value="">Error: ' + datasets.error + '</option>';
                        return;
                    }
                    _specDatasets = datasets;
                    console.log('[spec-browser] Loaded ' + datasets.length + ' datasets:', datasets.map(function(d) { return d.name; }));
                    if (datasets.length === 0) {
                        specDatasetSelect.innerHTML = '<option value="">No datasets found</option>';
                        console.warn('[spec-browser] No writable datasets returned');
                        return;
                    }
                    var html = '';
                    for (var i = 0; i < datasets.length; i++) {
                        html += '<option value="' + datasets[i].id + '" data-name="' + datasets[i].name + '" data-snapshot="' + (datasets[i].rwSnapshotId || '') + '" data-path="' + (datasets[i].datasetPath || '') + '">'
                            + datasets[i].name + '</option>';
                    }
                    specDatasetSelect.innerHTML = html;

                    var j;
                    for (j = 0; j < datasets.length; j++) {
                        if (datasets[j].name === 'autodoc') {
                            specDatasetSelect.value = datasets[j].id;
                            _specAutoDocSpecsId = datasets[j].id;
                            onDatasetChange();
                            return;
                        }
                    }
                    specDatasetSelect.selectedIndex = 0;
                    _specAutoDocSpecsId = datasets[0].id;
                    onDatasetChange();
                })
                .catch(function(err) {
                    console.error('[spec-browser] Failed to load datasets:', err);
                    specDatasetSelect.innerHTML = '<option value="">Failed to load datasets</option>';
                });
        }

        function onDatasetChange() {
            if (!specDatasetSelect) return;
            var opt = specDatasetSelect.options[specDatasetSelect.selectedIndex];
            console.log('[spec-browser] Dataset selected:', opt ? opt.getAttribute('data-name') : 'none');
            _specCurrentDatasetId = specDatasetSelect.value;
            _specCurrentDatasetName = opt ? opt.getAttribute('data-name') || '' : '';
            _specCurrentSnapshotId = opt ? opt.getAttribute('data-snapshot') || '' : '';
            _specCurrentDatasetPath = opt ? opt.getAttribute('data-path') || '' : '';
            _specCurrentPath = '';
            if (specPathField) specPathField.value = '';
            var svm = document.getElementById('spec-validation-msg');
            if (svm) svm.remove();
            if (_specCurrentDatasetId) {
                browseFiles('');
            } else {
                if (_specBrowseAbort) { _specBrowseAbort.abort(); _specBrowseAbort = null; }
                if (specFileList) specFileList.innerHTML = '<span class="spec-file-empty">Select a dataset to browse spec files</span>';
                if (specBreadcrumb) specBreadcrumb.innerHTML = '';
            }
        }

        function specParentPath(p) {
            if (!p) return null;
            var parts = p.split('/').filter(Boolean);
            if (parts.length === 0) return null;
            parts.pop();
            return parts.join('/');
        }

        function browseFiles(path) {
            _specCurrentPath = path;
            if (!specFileList) return Promise.resolve();
            if (!_specCurrentDatasetId) {
                specFileList.innerHTML = '<span class="spec-file-empty">Select a dataset to browse spec files</span>';
                return Promise.resolve();
            }
            console.log('[spec-browser] Browsing path:', path || '(root)', 'in dataset:', _specCurrentDatasetName);
            renderBreadcrumb(path);

            if (_specBrowseAbort) _specBrowseAbort.abort();
            var ctrl = _specBrowseAbort = new AbortController();
            specFileList.classList.add('spec-file-list-pending');
            return fetch(_adUrl('api/dataset-files') + queryApiDatasetFiles(path), { signal: ctrl.signal })
                .then(_checkResp).then(function(r) { return r.json(); })
                .then(function(files) {
                    if (!Array.isArray(files)) {
                        if (files && files.error) {
                            console.error('[spec-browser] File listing error:', files.error);
                            specFileList.innerHTML = '<span class="spec-file-empty">Error: ' + files.error + '</span>';
                        } else {
                            specFileList.innerHTML = '<span class="spec-file-empty">Unexpected response from server</span>';
                        }
                        return;
                    }
                    console.log('[spec-browser] Found ' + files.length + ' items at path:', path || '(root)');
                    if (files.length === 0) {
                        var emptyMsg = 'No YAML files found in this location';
                        var pPath = specParentPath(path);
                        if (pPath !== null) {
                            var up = '<div class="spec-file-item spec-file-parent" data-path="' + pPath + '" data-dir="true" data-name=".." data-parent="true">'
                                + '<span class="fa-icon fa-folder-open spec-file-icon"></span><span class="spec-file-name">..</span><span class="spec-file-size"></span></div>';
                            specFileList.innerHTML = up + '<span class="spec-file-empty">' + emptyMsg + '</span>';
                            var upEl = specFileList.querySelector('.spec-file-parent');
                            if (upEl) upEl.addEventListener('click', onFileClick);
                        } else {
                            specFileList.innerHTML = '<span class="spec-file-empty">' + emptyMsg + '</span>';
                        }
                        return;
                    }
                    var html = '';
                    var parentPath = specParentPath(path);
                    if (parentPath !== null) {
                        html += '<div class="spec-file-item spec-file-parent" data-path="' + parentPath + '" data-dir="true" data-name=".." data-parent="true">'
                            + '<span class="fa-icon fa-folder-open spec-file-icon"></span>'
                            + '<span class="spec-file-name">..</span>'
                            + '<span class="spec-file-size"></span></div>';
                    }
                    files.sort(function(a, b) {
                        if (a.isDirectory && !b.isDirectory) return -1;
                        if (!a.isDirectory && b.isDirectory) return 1;
                        return a.fileName.localeCompare(b.fileName);
                    });
                    for (var i = 0; i < files.length; i++) {
                        var f = files[i];
                        var iconClass = f.isDirectory ? 'fa-icon fa-folder-open spec-file-icon' : 'fa-icon fa-file-lines spec-file-icon';
                        var size = f.isDirectory ? '' : formatBytes(f.sizeInBytes || 0);
                        var fullPath = path ? path + '/' + f.fileName : f.fileName;
                        html += '<div class="spec-file-item" data-path="' + fullPath + '" data-dir="' + f.isDirectory + '" data-name="' + f.fileName + '">'
                            + '<span class="' + iconClass + '"></span>'
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
                    specFileList.innerHTML = '<span class="spec-file-empty">Failed to load files</span>';
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
                // Select this file
                var items = specFileList.querySelectorAll('.spec-file-item');
                for (var i = 0; i < items.length; i++) items[i].classList.remove('selected');
                el.classList.add('selected');
                selectSpecFile(path);
            }
        }

        function absoluteSpecFromRelative(relPath) {
            var base = (_specCurrentDatasetPath || '').replace(/\/+$/, '');
            var rel = (relPath || '').replace(/^\/+/, '');
            if (base) return rel ? (base + '/' + rel) : base;
            if (_specCurrentDatasetName && rel) return 'dataset://' + _specCurrentDatasetName + '/' + rel;
            return rel || '';
        }

        function selectSpecFile(relFilePath) {
            var abs = absoluteSpecFromRelative(relFilePath);
            console.log('[spec-browser] Selected:', abs);
            if (specSelectedIndicator) specSelectedIndicator.style.display = 'flex';
            if (specPathField) specPathField.value = abs;
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

        // Global for breadcrumb onclick
        window._specBrowse = function(path) { browseFiles(path); };

        // Upload from machine → autodoc dataset
        if (specMachineUpload) {
            specMachineUpload.addEventListener('change', function(e) {
                var file = e.target.files[0];
                if (!file) return;
                console.log('[spec-browser] Upload from machine:', file.name, '(' + file.size + ' bytes)');
                if (specUploadStatus) { specUploadStatus.textContent = 'Uploading ' + file.name + '...'; specUploadStatus.style.color = ''; specUploadStatus.className = 'spec-upload-status'; }

                var uploadDsId = _specCurrentDatasetId || _specAutoDocSpecsId;
                if (!uploadDsId) {
                    if (specUploadStatus) { specUploadStatus.textContent = 'Select a dataset first'; specUploadStatus.className = 'spec-upload-status spec-validation-empty'; specUploadStatus.style.color = ''; }
                    return;
                }
                var qs = queryApiDatasets();
                var fd = new FormData();
                fd.append('datasetId', uploadDsId);
                fd.append('relativeDir', _specCurrentPath || '');
                fd.append('file', file);
                fetch(_adUrl('api/upload-spec-to-dataset') + qs, { method: 'POST', body: fd })
                    .then(function(r) {
                        return r.json().catch(function() { return {}; }).then(function(j) {
                            return { ok: r.ok, j: j };
                        });
                    })
                    .then(function(o) {
                        var resultEl = document.getElementById('spec-validation-result');
                        if (!o.ok) {
                            if (o.j && o.j.errors && o.j.errors.length && resultEl) {
                                var verr = o.j.errors.map(function(e) { return '<li>' + e + '</li>'; }).join('');
                                resultEl.innerHTML = '<div class="spec-validation-error">'
                                    + '<span class="spec-selected-value">Spec validation failed</span>'
                                    + '<ul class="spec-validation-error-list">' + verr + '</ul>'
                                    + '</div>';
                            } else if (resultEl) {
                                resultEl.innerHTML = '';
                            }
                            var em = (o.j && o.j.error) ? o.j.error : 'Upload failed';
                            if (specUploadStatus) { specUploadStatus.textContent = em; specUploadStatus.className = 'spec-upload-status spec-validation-empty'; specUploadStatus.style.color = ''; }
                            var ev = new Error(em);
                            ev._uploadUiDone = true;
                            throw ev;
                        }
                        if (resultEl) resultEl.innerHTML = '<span class="spec-validation-success">Spec is valid</span>';
                        var result = o.j;
                        if (result.error) throw new Error(result.error);
                        console.log('[spec-browser] Upload success:', result.fileName, '→', result.path);
                        if (specUploadStatus) { specUploadStatus.textContent = 'Uploaded: ' + result.fileName; specUploadStatus.className = 'spec-upload-status spec-validation-success'; specUploadStatus.style.color = ''; }
                        var savedPath = result.path;
                        selectSpecFile(savedPath);
                        return browseFiles(_specCurrentPath).then(function() {
                            if (!savedPath || !specFileList) return;
                            var rows = specFileList.querySelectorAll('.spec-file-item');
                            for (var ri = 0; ri < rows.length; ri++) {
                                if (rows[ri].getAttribute('data-dir') === 'true') continue;
                                if (rows[ri].getAttribute('data-path') === savedPath) {
                                    for (var rj = 0; rj < rows.length; rj++) rows[rj].classList.remove('selected');
                                    rows[ri].classList.add('selected');
                                    break;
                                }
                            }
                        });
                    })
                    .catch(function(err) {
                        console.error('[spec-browser] Upload failed:', err.message);
                        if (err._uploadUiDone) return;
                        if (specUploadStatus) {
                            specUploadStatus.textContent = 'Upload failed: ' + err.message;
                            specUploadStatus.className = 'spec-upload-status spec-validation-empty';
                            specUploadStatus.style.color = '';
                        }
                    })
                    .finally(function() {
                        specMachineUpload.value = '';
                    });
            });
        }

        // Wire dataset select change; refresh job history when dataset changes
        if (specDatasetSelect) {
            specDatasetSelect.addEventListener('change', function() {
                onDatasetChange();
                fetchJobHistory();
            });
            loadDatasets();
        }

        // ── Toggle base URL and model name fields based on provider selection
        var OPENAI_DEFAULT_MODEL = 'gpt-5.4-mini';
        var ANTHROPIC_DEFAULT_MODEL = 'claude-haiku-4-5';
        function toggleOpenAIFields() {
            const isOpenAI = providerSelect && providerSelect.value === 'openai';
            var pbuInput = document.getElementById('field-provider_base_url');
            if (pbuInput) {
                var dkey = isOpenAI ? 'data-default-openai' : 'data-default-anthropic';
                var dflt = pbuInput.getAttribute(dkey);
                if (dflt) pbuInput.value = dflt;
            }
            if (modelNameField) {
                modelNameField.style.display = 'flex';
            }
            var modelInput = document.getElementById('field-model');
            if (modelInput) {
                var ph = isOpenAI ? OPENAI_DEFAULT_MODEL : ANTHROPIC_DEFAULT_MODEL;
                modelInput.placeholder = ph;
                var cur = (modelInput.value || '').trim();
                if (!cur) {
                    modelInput.value = ph;
                } else if (cur === OPENAI_DEFAULT_MODEL || cur === ANTHROPIC_DEFAULT_MODEL) {
                    modelInput.value = ph;
                }
            }
        }

        if (providerSelect) {
            providerSelect.addEventListener('change', toggleOpenAIFields);
            toggleOpenAIFields();
        }

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

        // ── Code root prefix select + suffix sync / browseCode options ─────
        (function() {
            const prefix = document.getElementById('code-root-prefix');
            const suffix = document.getElementById('code-root-suffix');
            const hidden = document.getElementById('field-code_root');
            function basePath() {
                if (!prefix) return '';
                if (prefix.tagName === 'SELECT') {
                    return (prefix.value || '').trim();
                }
                return (prefix.textContent || '').trim();
            }
            function sync() {
                if (!hidden) return;
                const base = basePath();
                const sub = suffix ? suffix.value.replace(/^\/+/, '') : '';
                hidden.value = sub ? base + '/' + sub : base;
            }
            function showCodeRootError() {
                if (!prefix || prefix.tagName !== 'SELECT') return;
                prefix.innerHTML = '';
                var opt = document.createElement('option');
                opt.value = '';
                opt.textContent = 'Could not retrieve source code';
                opt.disabled = true;
                opt.selected = true;
                prefix.appendChild(opt);
                prefix.classList.remove('code-root-loading');
                prefix.classList.add('code-root-error');
                if (hidden) hidden.value = '';
                sync();
                detectLanguageFromCodeRoot();
            }
            function showCodeRootLoading() {
                if (!prefix || prefix.tagName !== 'SELECT') return;
                prefix.innerHTML = '';
                var opt = document.createElement('option');
                opt.value = '';
                opt.textContent = 'Loading...';
                opt.disabled = true;
                opt.selected = true;
                prefix.appendChild(opt);
                prefix.classList.remove('code-root-error');
                prefix.classList.add('code-root-loading');
                if (hidden) hidden.value = '';
                sync();
            }
            function loadCodeRootOptions() {
                if (!prefix || prefix.tagName !== 'SELECT') return;
                var pid = new URLSearchParams(window.location.search).get('projectId');
                if (!pid) { showCodeRootError(); return; }
                showCodeRootLoading();
                var url = _adUrl('api/code-root-options') + '?projectId=' + encodeURIComponent(pid);
                fetch(url)
                    .then(_checkResp).then(function(r) { return r.json(); })
                    .then(function(data) {
                        if (data && data.error) { showCodeRootError(); return; }
                        var opts = (data && data.options) || [];
                        var defRoot = (data && data.defaultRoot) || (opts[0] && opts[0].value) || '';
                        if (!opts.length) { showCodeRootError(); return; }
                        prefix.classList.remove('code-root-error');
                        prefix.classList.remove('code-root-loading');
                        prefix.innerHTML = '';
                        for (var i = 0; i < opts.length; i++) {
                            var o = opts[i];
                            var opt = document.createElement('option');
                            opt.value = o.value || '';
                            opt.textContent = o.label || o.value || '';
                            prefix.appendChild(opt);
                        }
                        var pick = defRoot;
                        var found = false;
                        for (var j = 0; j < prefix.options.length; j++) {
                            if (prefix.options[j].value === pick) {
                                prefix.selectedIndex = j;
                                found = true;
                                break;
                            }
                        }
                        if (!found) prefix.selectedIndex = 0;
                        sync();
                        detectLanguageFromCodeRoot();
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
                prefix.addEventListener('change', function() {
                    sync();
                    detectLanguageFromCodeRoot();
                });
            }
            sync();
            loadCodeRootOptions();
        })();

        // ── Job history rendering ─────────────────────────────────────
        var _ACTIVE_STATUSES = {queued: true, submitted: true, pending: true, running: true};

        function _esc(s) {
            return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
        }

        function _jobRow(j) {
            var status = j.status || 'queued';
            var statusCls = 'history-status history-status-' + status;
            var branch = j.branch || '—';
            var tier = j.hardware_tier || '—';
            var submitted = j.submitted_at ? j.submitted_at.slice(0, 16).replace('T', ' ') : '—';
            var linkCell = j.job_url
                ? '<td><a href="' + _esc(j.job_url) + '" target="_blank">View →</a></td>'
                : '<td>—</td>';
            return '<tr>'
                + '<td title="' + _esc(branch) + '">' + _esc(branch) + '</td>'
                + '<td title="' + _esc(tier) + '">' + _esc(tier) + '</td>'
                + '<td><span class="' + statusCls + '">' + _esc(status.toUpperCase()) + '</span></td>'
                + '<td>' + _esc(submitted) + '</td>'
                + linkCell
                + '</tr>';
        }

        function _maxJobsWarning(jobs) {
            var hasQueued = jobs.some(function(j) { return j.status === 'queued' && !j.domino_run_id; });
            if (!hasQueued) return '';
            return '<div class="inline-callout inline-callout-warning" role="alert">'
                + '<span>⚠ </span>'
                + '<span>Job queued — a slot is occupied. It will start automatically when one opens. '
                + 'To free a slot, stop a running job or use </span>'
                + '<span class="spec-selected-value">Cancel queued</span>'
                + '<span> below.</span>'
                + '</div>';
        }

        function _tableHtml(jobs) {
            var header = '<thead><tr><th>Branch</th><th>Tier</th><th>Status</th><th>Submitted</th><th>Link</th></tr></thead>';
            var rows = jobs.map(function(j) { return _jobRow(j); }).join('');
            return '<table class="history-table">' + header + '<tbody>' + rows + '</tbody></table>';
        }

        function renderJobHistory(jobs) {
            var el = document.getElementById('job-history-content');
            if (!el) return;

            var prevDetailsOpen = false;
            var prevCompletedCount = 0;
            var details = el.querySelector('details');
            if (details) {
                prevDetailsOpen = details.open;
                prevCompletedCount = details.querySelectorAll('tbody tr').length;
            }

            if (!jobs || !jobs.length) {
                el.innerHTML = '<div class="spec-file-empty"><span class="fa-icon fa-file-lines spec-file-empty-icon"></span><span class="spec-file-list-empty">No autodocs generated yet.</span></div>';
                return;
            }

            var activeJobs = jobs.filter(function(j) { return _ACTIVE_STATUSES[j.status || 'queued']; });
            var completedJobs = jobs.filter(function(j) { return !_ACTIVE_STATUSES[j.status || 'queued']; });
            var hasQueued = jobs.some(function(j) { return j.status === 'queued' && !j.domino_run_id; });

            var html = _maxJobsWarning(jobs);

            if (activeJobs.length) {
                html += '<div class="history-table-wrap">' + _tableHtml(activeJobs) + '</div>';
            }
            if (completedJobs.length) {
                var n = completedJobs.length;
                var label = 'Show ' + n + ' completed job' + (n !== 1 ? 's' : '');
                var autoOpen = !activeJobs.length || prevDetailsOpen || completedJobs.length > prevCompletedCount;
                html += '<details' + (autoOpen ? ' open' : '') + '>'
                    + '<summary class="history-toggle">' + label + '</summary>'
                    + '<div class="history-table-wrap">' + _tableHtml(completedJobs) + '</div>'
                    + '</details>';
            }

            var actions = '<a class="terminal-action" title="Refresh job status from Domino" id="job-history-refresh-btn" href="#">Refresh</a>';
            if (hasQueued) {
                actions += ' <a class="terminal-action" title="Cancel all queued jobs that haven\'t been submitted yet" id="job-cancel-queued-btn" href="#">Cancel queued</a>';
            }
            html += '<div class="history-actions">' + actions + '</div>';

            el.innerHTML = html;

            // Wire refresh button
            var refreshBtn = el.querySelector('#job-history-refresh-btn');
            if (refreshBtn) {
                refreshBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    fetchJobHistory();
                });
            }

            // Wire cancel queued button
            var cancelBtn = el.querySelector('#job-cancel-queued-btn');
            if (cancelBtn) {
                cancelBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    fetch(_adUrl('cancel-queued-jobs') + queryJobHistory(), { method: 'POST' })
                        .then(_checkResp).then(function(r) { return r.json(); })
                        .then(function(data) { renderJobHistory(data.jobs || []); })
                        .catch(function() {});
                });
            }
        }

        function fetchJobHistory() {
            fetch(_adUrl('job-history') + queryJobHistory())
                .then(_checkResp).then(function(r) { return r.json(); })
                .then(function(data) { renderJobHistory(data.jobs || []); })
                .catch(function() {});
        }

        // Poll job history every 10 seconds
        setInterval(fetchJobHistory, 10000);

        function runJobJsonPayloadFromMainForm(resolvedSpecPath) {
            function val(id) {
                var el = document.getElementById(id);
                return el ? String(el.value || '').trim() : '';
            }
            function chk(id) {
                var el = document.getElementById(id);
                return !!(el && el.checked);
            }
            return {
                spec_path: resolvedSpecPath,
                provider: val('field-provider'),
                model: val('field-model'),
                code_root: val('field-code_root'),
                max_files: val('field-max_files'),
                workers: val('field-workers'),
                planning_workers: val('field-planning_workers'),
                timeout: val('field-timeout'),
                notebook: chk('field-notebook'),
                notebook_path: val('field-notebook_path'),
                filtered_experiment_names: val('field-filtered_experiment_names'),
                filtered_model_names: val('field-filtered_model_names'),
                latest_only: chk('field-latest_only'),
                verbose: chk('field-verbose'),
                branch: val('field-branch'),
                hardware_tier: val('field-hardware_tier'),
                environment_id: val('field-environment_id'),
                environment_revision_id: val('field-environment_revision_id'),
                provider_base_url: val('field-provider_base_url'),
                language: val('field-language'),
                max_retries: val('field-max_retries'),
                initial_backoff: val('field-initial_backoff'),
                max_backoff: val('field-max_backoff'),
                backoff_jitter: val('field-backoff_jitter'),
                notebook_from_cache: chk('field-notebook_from_cache'),
            };
        }

        // ── Form submission ───────────────────────────────────────────
        var mainForm = document.getElementById('main-form');
        if (mainForm) {
            mainForm.addEventListener('submit', function(e) {
                e.preventDefault();

                var specPath = document.getElementById('field-spec_path');
                var hasSpec = specPath && specPath.value.trim();
                if (!hasSpec) {
                    var msg = 'Please select or upload a spec file before generating documentation.';
                    var existing = document.getElementById('spec-validation-msg');
                    if (!existing) {
                        var indicator = document.getElementById('spec-selected-indicator');
                        if (indicator) {
                            var msgEl = document.createElement('div');
                            msgEl.id = 'spec-validation-msg';
                            msgEl.className = 'spec-validation-msg';
                            msgEl.textContent = msg;
                            indicator.parentNode.insertBefore(msgEl, indicator.nextSibling);
                        } else {
                            alert(msg);
                        }
                    }
                    return;
                }
                var existingMsg = document.getElementById('spec-validation-msg');
                if (existingMsg) existingMsg.remove();

                var rawSpec = (specPath && specPath.value || '').trim();
                var resolvedSpec = rawSpec;
                if (rawSpec.indexOf('dataset://') === 0 && _specCurrentDatasetPath) {
                    var rest = rawSpec.slice('dataset://'.length);
                    var si = rest.indexOf('/');
                    var rel = si >= 0 ? rest.slice(si + 1) : '';
                    var base = _specCurrentDatasetPath.replace(/\/+$/, '');
                    resolvedSpec = rel ? (base + '/' + rel) : base;
                }
                var pid = resolvedProjectId();
                var jsonPayload = runJobJsonPayloadFromMainForm(resolvedSpec);

                var qs = pid ? ('?projectId=' + encodeURIComponent(pid)) : '';
                var submitBtn = mainForm.querySelector('[type=submit]');
                var runMsgEl = document.getElementById('generate-run-message');
                function setRunMessage(text, isError) {
                    if (!runMsgEl) return;
                    runMsgEl.textContent = text || '';
                    if (isError) {
                        runMsgEl.classList.add('generate-run-message--error');
                    } else {
                        runMsgEl.classList.remove('generate-run-message--error');
                    }
                }
                setRunMessage('', false);
                if (submitBtn) submitBtn.disabled = true;

                fetch(_adUrl('run') + qs, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(jsonPayload),
                })
                    .then(function(r) {
                        return r.text().then(function(text) {
                            var data = null;
                            try {
                                data = text ? JSON.parse(text) : null;
                            } catch (e) {}
                            if (!r.ok) {
                                var err = (data && data.error) ? data.error : ('Request failed (' + r.status + ')');
                                setRunMessage(err, true);
                                throw new Error(err);
                            }
                            setRunMessage('', false);
                            return data;
                        });
                    })
                    .then(function() { fetchJobHistory(); })
                    .catch(function() {})
                    .finally(function() { if (submitBtn) submitBtn.disabled = false; });
            });
        }
    });
"""
