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
    // Applies to <a href>, <form action>, and htmx hx-post/hx-get.
    function _adApplyPrefix(root) {
        var scope = root || document;
        scope.querySelectorAll('[data-app-rel]').forEach(function(el) {
            var rel = el.getAttribute('data-app-rel');
            if (!rel) return;
            var full = _adUrl(rel);
            if (el.tagName === 'A') el.setAttribute('href', full);
            else if (el.tagName === 'FORM') el.setAttribute('action', full);
            if (el.hasAttribute('hx-post')) el.setAttribute('hx-post', full);
            if (el.hasAttribute('hx-get')) el.setAttribute('hx-get', full);
        });
    }
    document.addEventListener('DOMContentLoaded', function() { _adApplyPrefix(); });

    document.addEventListener('DOMContentLoaded', function() {

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
            // 1. Own query string (direct / non-proxied access)
            pid = new URLSearchParams(window.location.search).get('projectId');
            // 2. Own hash fragment (#projectId=xxx — survives proxies)
            if (!pid && window.location.hash) {
                var h = window.location.hash.substring(1);
                if (h.charAt(0) === '?') h = h.substring(1);
                pid = new URLSearchParams(h).get('projectId');
            }
            // 3. Parent frame (same-origin deployments where parent
            //    and iframe share the same host)
            if (!pid && window.parent !== window) {
                try {
                    var pLoc = window.parent.location;
                    pid = new URLSearchParams(pLoc.search).get('projectId');
                    if (!pid && pLoc.hash) {
                        var ph = pLoc.hash.substring(1);
                        if (ph.charAt(0) === '?') ph = ph.substring(1);
                        pid = new URLSearchParams(ph).get('projectId');
                    }
                } catch(e) { /* cross-origin — ignore */ }
            }
            if (pid) {
                setProjectId(pid);
            }
            // 4. Listen for postMessage from Domino parent frame
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
            if (_specCurrentDatasetId) parts.push('datasetId=' + encodeURIComponent(_specCurrentDatasetId));
            if (_specCurrentSnapshotId) parts.push('snapshotId=' + encodeURIComponent(_specCurrentSnapshotId));
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
                                + '<span class="spec-file-icon">\ud83d\udcc1</span><span class="spec-file-name">..</span><span class="spec-file-size"></span></div>';
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
                            + '<span class="spec-file-icon">\ud83d\udcc1</span>'
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
                // Validate spec content before uploading
                if (typeof validateSpecContent === 'function') validateSpecContent(file);

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
                    .then(_checkResp).then(function(r) { return r.json(); })
                    .then(function(result) {
                        if (result.error) throw new Error(result.error);
                        console.log('[spec-browser] Upload success:', result.fileName, '→', result.path);
                        if (specUploadStatus) { specUploadStatus.textContent = 'Uploaded: ' + result.fileName; specUploadStatus.className = 'spec-upload-status spec-validation-success'; specUploadStatus.style.color = ''; }
                        var dsName = _specCurrentDatasetName || 'dataset';
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
                        if (specUploadStatus) { specUploadStatus.textContent = 'Upload failed: ' + err.message; specUploadStatus.className = 'spec-upload-status spec-validation-empty'; specUploadStatus.style.color = ''; }
                    })
                    .finally(function() {
                        specMachineUpload.value = '';
                    });
            });
        }

        // Wire dataset select change
        if (specDatasetSelect) {
            specDatasetSelect.addEventListener('change', onDatasetChange);
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
                modelInput.placeholder = isOpenAI ? OPENAI_DEFAULT_MODEL : ANTHROPIC_DEFAULT_MODEL;
            }
        }

        if (providerSelect) {
            providerSelect.addEventListener('change', toggleOpenAIFields);
            toggleOpenAIFields();
        }

        // ── Spec validation helper ────────────────────────────────────
        window._specValid = true;
        function validateSpecContent(file) {
            var fd = new FormData();
            fd.append('spec_upload', file);
            var resultEl = document.getElementById('spec-validation-result');
            if (resultEl) resultEl.innerHTML = '<span class="spec-validation-pending">Validating spec...</span>';
            fetch(_adUrl('validate-spec'), { method: 'POST', body: fd })
                .then(_checkResp).then(function(r) { return r.text(); })
                .then(function(html) {
                    if (resultEl) resultEl.outerHTML = html;
                    window._specValid = html.indexOf('validation failed') === -1;
                })
                .catch(function() {
                    if (resultEl) resultEl.innerHTML = '';
                    window._specValid = true;
                });
        }

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

        // Block form submission when no spec is selected
        document.body.addEventListener('htmx:confirm', function(e) {
            var form = e.detail.elt;
            if (form.id !== 'main-form') return;
            var specPath = document.getElementById('field-spec_path');
            var specUpload = document.getElementById('spec-machine-upload');
            var hasSpec = (specPath && specPath.value.trim()) ||
                          (specUpload && specUpload.files && specUpload.files.length > 0);
            if (!hasSpec) {
                e.preventDefault();
                var msg = 'Please select or upload a spec file before generating documentation.';
                var existing = document.getElementById('spec-validation-msg');
                if (!existing) {
                    var indicator = document.getElementById('spec-selected-indicator');
                    if (indicator) {
                        var el = document.createElement('div');
                        el.id = 'spec-validation-msg';
                        el.className = 'spec-validation-msg';
                        el.textContent = msg;
                        indicator.parentNode.insertBefore(el, indicator.nextSibling);
                    } else {
                        alert(msg);
                    }
                }
            } else {
                var existing = document.getElementById('spec-validation-msg');
                if (existing) existing.remove();
            }
        });

        // Ensure every HTMX request carries projectId from the page URL so
        // server handlers never fall back to process-global state that may
        // belong to a different user.
        document.body.addEventListener('htmx:configRequest', function(e) {
            var pid = new URLSearchParams(window.location.search).get('projectId');
            if (pid) {
                var path = e.detail.path || '';
                if (!/[?&]projectId=/.test(path)) {
                    e.detail.path = path + (path.indexOf('?') >= 0 ? '&' : '?') +
                        'projectId=' + encodeURIComponent(pid);
                }
            }
            if (_specCurrentDatasetId) {
                e.detail.parameters['datasetId'] = _specCurrentDatasetId;
            }
            if (_specCurrentSnapshotId) {
                e.detail.parameters['snapshotId'] = _specCurrentSnapshotId;
            }
            if (_specCurrentDatasetPath) {
                e.detail.parameters['datasetPath'] = _specCurrentDatasetPath;
            }
        });

        // Poll job history — pause while an HTMX request targets the history panel
        var _htmxBusy = false;
        document.body.addEventListener('htmx:beforeRequest', function(e) {
            var tgt = e.detail && e.detail.target;
            if (tgt && tgt.id === 'job-history-content') _htmxBusy = true;
        });
        document.body.addEventListener('htmx:afterRequest', function(e) {
            var tgt = e.detail && e.detail.target;
            if (tgt && tgt.id === 'job-history-content') _htmxBusy = false;
        });
        setInterval(function() {
            if (_htmxBusy) return;
            var el = document.getElementById('job-history-content');
            if (!el) return;
            // Preserve <details> open state; auto-open when completed count changes
            var wasOpen = false;
            var prevCount = 0;
            var details = el.querySelector('details');
            if (details) {
                wasOpen = details.open;
                prevCount = details.querySelectorAll('tbody tr').length;
            }
            fetch(_adUrl('job-history') + queryJobHistory())
                .then(_checkResp).then(function(r) { return r.text(); })
                .then(function(html) {
                    if (!_htmxBusy) {
                        el.innerHTML = html;
                        var d = el.querySelector('details');
                        if (d) {
                            var newCount = d.querySelectorAll('tbody tr').length;
                            if (wasOpen || newCount > prevCount) d.open = true;
                        }
                        if (window.htmx) htmx.process(el);
                    }
                })
                .catch(function() {});
        }, 10000);
    });
"""
