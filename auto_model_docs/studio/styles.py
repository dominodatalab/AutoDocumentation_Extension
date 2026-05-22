"""Blueprint Enterprise Design System CSS for the Stitch UI."""

from __future__ import annotations

STUDIO_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');

:root {
    /* Primary palette */
    --primary: #543fde;
    --primary-hover: #3b23d1;
    --primary-active: #311eae;
    --primary-container: #edeafb;
    --on-primary: #ffffff;
    --on-primary-container: #311eae;
    --primary-fixed: #f0eefc;
    --primary-fixed-dim: #d1cbf6;

    /* Surfaces — tonal layering */
    --surface: #f8f8fc;
    --surface-container-lowest: #ffffff;
    --surface-container-low: #f7f7fb;
    --surface-container: #f1f2f8;
    --surface-container-high: #e9ebf2;
    --surface-container-highest: #dfe3ee;
    --surface-dim: #cdd3df;
    --surface-variant: #eef1f6;
    --on-surface: #2e2e38;
    --on-surface-variant: #65657b;
    --muted: #8f8fa3;

    /* Outline */
    --outline: #7f8385;
    --outline-variant: #dbe4e8;
    --ghost-border: rgba(219, 228, 232, 0.85);

    /* Semantic */
    --error: #c20a29;
    --error-container: #fce8ec;
    --on-error-container: #8e1630;
    --tertiary: #0070cc;
    --tertiary-container: #e8f1fb;
    --tertiary-fixed: #d9ebff;
    --secondary: #1820a0;
    --secondary-container: #edeafb;
    --on-secondary-container: #311eae;

    /* Functional */
    --success: #28A464;
    --success-container: #e8f6ee;
    --warning: #CCB718;
    --warning-container: #fff4db;
    --info: #0070CC;
    --info-container: #e8f1fb;

    /* Typography */
    --font-headline: 'Inter', 'Lato', 'Helvetica Neue', Helvetica, Arial, sans-serif;
    --font-body: 'Inter', 'Lato', 'Helvetica Neue', Helvetica, Arial, sans-serif;

    /* Ambient shadows */
    --shadow-sm: 0 1px 2px rgba(46, 46, 56, 0.04), 0 8px 24px rgba(46, 46, 56, 0.04);
    --shadow-md: 0 8px 24px rgba(46, 46, 56, 0.08);
    --shadow-lg: 0 16px 40px rgba(46, 46, 56, 0.12);
    --shadow-float: 0 20px 48px rgba(46, 46, 56, 0.16);
    --radius-sm: 4px;
    --radius-md: 8px;
    --radius-lg: 12px;
}

/* ── Reset & Base ─────────────────────────────────────────────────── */
html, body {
    margin: 0;
    padding: 0;
    min-height: 100vh;
    background: var(--surface);
    color: var(--on-surface);
    font-family: var(--font-body);
    font-size: 14px;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
}

*, *::before, *::after { box-sizing: border-box; }

h1, h2, h3, h4 {
    font-family: var(--font-headline);
    color: var(--on-surface);
    margin: 0;
    font-weight: 700;
}

a {
    color: var(--primary);
    text-decoration: none;
    transition: color 0.2s ease;
}
a:hover { color: var(--primary-container); }

/* Material icon baseline */
.material-symbols-outlined {
    font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
    vertical-align: middle;
}

/* ── Header ───────────────────────────────────────────────────────── */
.domino-header {
    background: #2e2e38;
    width: 100%;
    height: 44px;
    padding: 0 1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-sizing: border-box;
    flex-shrink: 0;
}
.domino-header-inner {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 0.75rem;
}

.domino-header-inner svg {
    height: 32px;
    width: auto;
    display: block;
    flex-shrink: 0;
}
.domino-header-title {
    color: #ffffff;
    font-family: var(--font-headline);
    font-size: 14px;
    font-weight: 600;
    letter-spacing: -0.01em;
    margin: 0;
}
.domino-header-subtitle {
    font-family: var(--font-body);
    font-size: 12px;
    font-weight: 400;
    color: rgba(255, 255, 255, 0.5);
    margin: 0;
}
.domino-header-version {
    font-family: var(--font-body);
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--secondary);
    background: var(--secondary-container);
    padding: 2px 8px;
    border-radius: var(--radius-sm);
}

/* ── Page title (H1 inside content, below the nav bar) ───────────── */
.page-title {
    font-size: 24px;
    font-weight: 700;
    color: var(--on-surface);
    letter-spacing: -0.02em;
    margin: 0 0 1.25rem 0;
}

/* ── Page Layout ──────────────────────────────────────────────────── */
.page {
    padding: 2rem 1.5rem 1.5rem;
    width: 100%;
    min-height: calc(100vh - 100px);
    display: flex;
    flex-direction: column;
    box-sizing: border-box;
}
.studio-footer-meta {
    margin-top: auto;
    padding-top: 2.5rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
}
.studio-page-insight {
    width: 100%;
    margin-bottom: 1.25rem;
}
.studio-page-insight .insight-card {
    margin-top: 0;
}
.hero {
    padding: 0.25rem 0 1rem 0;
}
.hero-tagline {
    font-family: var(--font-body);
    font-size: 14px;
    font-weight: 400;
    color: var(--on-surface-variant);
    margin: 0;
    line-height: 1.5;
}

.target-project-callout {
    margin-bottom: 0.5rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid var(--outline-variant);
}
.target-project-row {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.25rem 0.35rem;
    line-height: 1.35;
}
.target-project-label-prefix {
    color: var(--on-surface);
    font-size: inherit;
    font-weight: inherit;
}
.target-project-display {
    font-size: inherit;
    font-weight: inherit;
    color: var(--primary);
    letter-spacing: -0.01em;
}

.env-revision-row {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    align-items: flex-start;
    margin-bottom: 1rem;
}
.env-revision-row > .field {
    flex: 1 1 200px;
    min-width: 0;
    margin-bottom: 0;
}
.env-revision-row > .field > .label-row {
    min-height: 1.5rem;
    align-items: center;
}
#environment-revision-slot {
    display: contents;
}

/* ── 3-Column Grid ────────────────────────────────────────────────── */
.studio-grid {
    display: grid;
    grid-template-columns: minmax(280px, 3fr) minmax(420px, 5fr) minmax(320px, 4fr);
    gap: 1.25rem;
    align-items: stretch;
}
.studio-col-left,
.studio-col-mid,
.studio-col-right {
    display: flex;
    flex-direction: column;
    min-height: 0;
}
.studio-col-left > .bp-card,
.studio-col-mid > .bp-card {
    flex: 1 1 auto;
    min-height: 0;
    display: flex;
    flex-direction: column;
}
.card-content-spacer {
    flex: 1;
    min-height: 2rem;
}
@media (max-width: 1200px) {
    .studio-grid {
        grid-template-columns: 1fr 1fr;
    }
    .studio-grid .studio-col-right {
        grid-column: 1 / -1;
    }
}
@media (max-width: 800px) {
    .studio-grid {
        grid-template-columns: 1fr;
    }
}

/* ── Column Headers ───────────────────────────────────────────────── */
.col-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin-bottom: 0.875rem;
    padding: 0 0.125rem;
}
.col-header h2 {
    font-family: var(--font-headline);
    font-size: 16px;
    font-weight: 700;
    color: var(--on-surface);
    letter-spacing: -0.01em;
}
.step-badge {
    font-family: var(--font-body);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: var(--muted);
    flex-shrink: 0;
}

/* ── Card section headings (H3) ───────────────────────────────────── */
.bp-card h3 {
    font-size: 16px;
    font-weight: 600;
    color: var(--on-surface);
    margin: 0 0 0.625rem 0;
    letter-spacing: -0.01em;
}

/* ── Cards (No-Line Rule: tonal layering, not borders) ───────────── */
.bp-card {
    background: var(--surface-container-lowest);
    border: 1px solid var(--outline-variant);
    border-radius: var(--radius-sm);
    padding: 1.5rem;
    box-shadow: var(--shadow-sm);
    transition: box-shadow 0.2s ease;
}
.bp-card:hover {
    box-shadow: var(--shadow-md);
}

/* ── Form Fields ──────────────────────────────────────────────────── */
.field {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    margin-bottom: 1rem;
}
.field:last-child {
    margin-bottom: 0;
}
.field > label,
.field .label-row > label {
    font-family: var(--font-body);
    font-size: 13px;
    font-weight: 500;
    text-transform: none;
    letter-spacing: normal;
    color: var(--on-surface);
}
input[type="text"]:not(.code-root-suffix),
input[type="number"],
input[type="password"],
textarea {
    background-color: #ffffff;
    border: 1px solid #d6d6d6;
    border-radius: 4px;
    padding: 0 14px;
    height: 36px;
    color: #2e2e38;
    font-family: var(--font-body);
    font-size: 14px;
    font-weight: 400;
    transition: border-color 0.15s ease;
    outline: none;
    min-width: 0;
    width: 100%;
    box-sizing: border-box;
    -webkit-appearance: none;
    appearance: none;
}
select:not(.code-root-prefix):not(.lang-override-select) {
    background-color: #ffffff;
    border: 1px solid #d6d6d6;
    border-radius: 4px;
    padding: 0 2rem 0 14px;
    height: 36px;
    color: #2e2e38;
    font-family: var(--font-body);
    font-size: 14px;
    font-weight: 400;
    transition: border-color 0.15s ease;
    outline: none;
    min-width: 0;
    width: 100%;
    box-sizing: border-box;
    -webkit-appearance: none;
    appearance: none;
    cursor: pointer;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%2365657b' stroke-width='1.5' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 0.75rem center;
}
textarea {
    height: auto;
    padding: 8px 14px;
    min-height: 72px;
}
input[type="text"]:not(.code-root-suffix):hover,
input[type="number"]:hover,
input[type="password"]:hover,
select:not(.code-root-prefix):not(.lang-override-select):hover,
textarea:hover {
    border-color: #543fde;
}
input[type="text"]:not(.code-root-suffix):focus,
input[type="number"]:focus,
input[type="password"]:focus,
select:not(.code-root-prefix):not(.lang-override-select):focus,
textarea:focus {
    border-color: #543fde;
    box-shadow: none;
    outline: none;
}
input[type="text"]::placeholder,
input[type="number"]::placeholder,
input[type="password"]::placeholder,
textarea::placeholder {
    color: #65657b;
    font-size: 14px;
    font-weight: 400;
}
input:disabled,
select:disabled,
textarea:disabled {
    background: #ebebeb;
    color: #65657b;
    border-color: #65657b;
    cursor: not-allowed;
}
input[type="checkbox"],
input[type="radio"] {
    appearance: auto;
    -webkit-appearance: auto;
    width: auto;
    border: none;
    background: none;
    padding: 0;
    border-radius: 0;
}
input[type="file"] {
    display: none !important;
}
.field-hint-text {
    display: block;
    font-size: 12px;
    color: var(--outline);
    margin-top: 0.15rem;
    margin-bottom: 0.5rem;
}

/* Code root combo */
.code-root-wrap {
    display: flex;
    border: 1px solid #d6d6d6;
    border-radius: 4px;
    overflow: hidden;
    background: #ffffff;
    transition: border-color 0.15s ease;
    height: 36px;
}
.code-root-wrap:hover {
    border-color: #543fde;
}
.code-root-wrap:focus-within {
    border-color: #543fde;
    box-shadow: none;
}
.code-root-prefix {
    padding: 0 2rem 0 14px;
    height: 36px;
    background: var(--surface-container-low);
    border: none;
    border-right: 1px solid #d6d6d6;
    font-size: 14px;
    color: #543fde;
    font-family: var(--font-body);
    white-space: nowrap;
    user-select: none;
    min-width: 6.5rem;
    max-width: 55%;
    flex-shrink: 0;
    cursor: pointer;
    -webkit-appearance: none;
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%2365657b' stroke-width='1.5' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 0.75rem center;
    outline: none;
}
.code-root-prefix option {
    font-family: var(--font-body);
}
.code-root-prefix.code-root-error {
    color: var(--on-surface);
}
.code-root-prefix.code-root-loading {
    color: var(--on-surface-variant);
}
.code-root-suffix {
    flex: 1;
    border: none;
    padding: 0 14px;
    height: 36px;
    font-size: 14px;
    color: #2e2e38;
    background: transparent;
    outline: none;
    min-width: 0;
    font-family: var(--font-body);
}
.code-root-suffix::placeholder { color: #65657b; }

/* Label row with info tooltip */
.label-row {
    display: flex;
    align-items: center;
    gap: 0.35rem;
}
.required-star {
    color: var(--error);
    font-weight: 600;
}
.info-tooltip {
    position: relative;
    cursor: help;
    color: var(--outline);
    font-size: 12px;
    line-height: 1;
}
#studio-info-tooltip {
    position: fixed;
    left: 0;
    top: 0;
    z-index: 10050;
    padding: 0.5rem 0.75rem;
    background: var(--on-surface);
    color: var(--surface-container-lowest);
    font-size: 12px;
    font-weight: 400;
    white-space: normal;
    min-width: 200px;
    max-width: min(320px, calc(100vw - 16px));
    width: max-content;
    border-radius: var(--radius-sm);
    pointer-events: none;
    opacity: 0;
    visibility: hidden;
    transition: opacity 0.15s ease, visibility 0.15s ease;
    box-shadow: var(--shadow-md);
    font-family: var(--font-body);
    text-transform: none;
    letter-spacing: normal;
    box-sizing: border-box;
}
#studio-info-tooltip.visible {
    opacity: 1;
    visibility: visible;
}
.env-revision-label-spacer {
    visibility: hidden;
    pointer-events: none;
    user-select: none;
}

/* Inline upload row */
.field-inline {
    display: flex;
    gap: 0.5rem;
    align-items: stretch;
}
.field-inline input[type="text"] {
    flex: 1;
    min-width: 0;
}
.upload-btn {
    background: transparent;
    border: 1px solid var(--primary);
    border-radius: var(--radius-sm);
    padding: 0 16px;
    height: 32px;
    color: var(--primary);
    font-family: var(--font-body);
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.15s ease, color 0.15s ease;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    text-decoration: none;
    white-space: nowrap;
    box-sizing: border-box;
}
.upload-btn:hover {
    background: var(--primary-fixed);
    color: var(--primary-active);
}
.hidden-upload {
    display: none !important;
}
.upload-filename {
    font-size: 12px;
    color: var(--primary);
    margin-top: 0.25rem;
}

/* ── Drag-drop zone ───────────────────────────────────────────────── */
.drop-zone {
    position: relative;
    border: 1px dashed var(--primary-fixed-dim);
    border-radius: var(--radius-md);
    padding: 2rem 1.5rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    cursor: pointer;
    transition: border-color 0.2s ease, background 0.2s ease;
    background: transparent;
    min-height: 160px;
}
.drop-zone:hover {
    border-color: var(--primary);
    background: rgba(84, 63, 222, 0.03);
}
.drop-zone-icon {
    color: var(--primary);
    font-size: 2rem;
    margin-bottom: 0.5rem;
}
.drop-zone-text {
    font-size: 13px;
    font-weight: 600;
    color: var(--on-surface);
}
.drop-zone-hint {
    font-size: 10px;
    color: var(--outline);
    margin-top: 0.25rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* ── Spec browser ─────────────────────────────────────────────────── */
.spec-breadcrumb {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: var(--outline);
    padding: 4px 0;
    flex-wrap: wrap;
}
.spec-breadcrumb-link {
    color: var(--primary);
    cursor: pointer;
    text-decoration: none;
}
.spec-breadcrumb-link:hover { text-decoration: underline; }
.spec-breadcrumb-sep { color: var(--outline-variant); margin: 0 2px; }
.spec-breadcrumb-current { color: var(--on-surface); font-weight: 600; }
.spec-file-list {
    --spec-file-row: 2.75rem;
    border: 1px solid var(--outline-variant);
    border-radius: var(--radius-md);
    height: calc(5 * var(--spec-file-row));
    min-height: calc(5 * var(--spec-file-row));
    overflow-y: auto;
    background: var(--surface-container-lowest);
    display: flex;
    flex-direction: column;
}
.spec-file-list.spec-file-list-pending {
    pointer-events: none;
    opacity: 0.55;
    transition: opacity 0.12s ease;
}
.spec-file-list > .spec-file-empty {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 0;
    box-sizing: border-box;
}
.spec-file-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    font-size: 13px;
    cursor: pointer;
    transition: background 0.1s;
    min-height: var(--spec-file-row);
    box-sizing: border-box;
    flex-shrink: 0;
}
.spec-file-parent .spec-file-name {
    color: var(--on-surface-variant);
    font-weight: 600;
}
.spec-file-item + .spec-file-item {
    border-top: 1px solid var(--ghost-border);
}
.spec-file-list > .spec-file-item:last-of-type {
    border-bottom: 1px solid var(--ghost-border);
}
.spec-file-item:hover { background: var(--surface-container-low); }
.spec-file-item.selected {
    background: var(--primary-fixed);
    color: var(--primary-active);
}
.spec-file-icon { flex-shrink: 0; width: 18px; text-align: center; }
.spec-file-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.spec-file-size { color: var(--outline); font-size: 12px; flex-shrink: 0; }
.spec-file-empty {
    padding: 24px 12px;
    text-align: center;
    color: var(--on-surface);
    font-size: 13px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.375rem;
}
.spec-file-empty-icon {
    font-size: 1.75rem;
    color: var(--surface-dim);
    font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24;
}
.spec-actions-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding-top: 8px;
    flex-wrap: wrap;
}
.spec-upload-status {
    font-size: 13px;
    color: var(--on-surface);
}
.spec-validation-error {
    background: var(--error-container);
    border-left: 3px solid var(--error);
    border-radius: var(--radius-sm);
    padding: 0.5rem 0.75rem;
    margin-top: 0.375rem;
    font-size: 13px;
    color: var(--on-surface);
}
.spec-validation-error ul { color: var(--on-surface); }
.spec-validation-error-list {
    margin: 0.25rem 0 0 0;
    padding-left: 1.25rem;
    font-size: 13px;
}

/* Spec info rows */
.spec-info {
    padding-top: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}
.spec-info-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 13px;
}
.spec-info-label {
    color: var(--outline);
    font-weight: 400;
}
.spec-info-value {
    font-family: var(--font-headline);
    font-weight: 700;
    color: var(--primary);
}
.spec-info-badge {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 2px 8px;
    border-radius: var(--radius-sm);
}
.spec-info-badge-valid {
    background: rgba(40, 164, 100, 0.1);
    color: var(--success);
}
.spec-info-badge-invalid {
    background: rgba(186, 26, 26, 0.1);
    color: var(--on-surface);
}

/* ── Checkbox ─────────────────────────────────────────────────────── */
.checkbox-field {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    margin-bottom: 1rem;
    cursor: pointer;
    font-size: 13px;
    font-weight: 400;
    color: var(--on-surface);
    text-transform: none;
    letter-spacing: normal;
}
.checkbox-field input[type="checkbox"] {
    width: 1rem;
    height: 1rem;
    min-width: 1rem;
    accent-color: var(--primary);
    cursor: pointer;
    flex-shrink: 0;
}
.checkbox-field span {
    color: var(--on-surface);
    font-size: 13px;
    font-weight: 400;
}
.field-hint {
    margin-top: -0.5rem;
    margin-bottom: 1rem;
    padding-left: 1.625rem;
}
.field-hint.hidden { display: none; }

/* ── Advanced / Collapsible Sections ──────────────────────────────── */
.advanced-section {
    margin-top: 0.75rem;
    background: var(--surface-container-lowest);
    border: 1px solid var(--outline-variant);
    border-radius: var(--radius-md);
    overflow: hidden;
}
.advanced-section summary {
    font-family: var(--font-body);
    font-size: 13px;
    font-weight: 600;
    text-transform: none;
    letter-spacing: normal;
    color: var(--on-surface-variant);
    cursor: pointer;
    padding: 0.75rem 1rem;
    list-style: none;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: var(--surface-container-low);
    transition: color 0.2s ease, background 0.2s ease;
}
.advanced-section summary::-webkit-details-marker {
    display: none;
}
.advanced-section summary::before {
    content: '\u25B6';
    font-size: 8px;
    transition: transform 0.2s ease;
}
.advanced-section[open] summary::before {
    transform: rotate(90deg);
}
.advanced-section summary:hover {
    color: var(--primary);
    background: var(--surface-container);
}
.advanced-summary-desc {
    font-weight: 400;
    font-size: 12px;
    color: var(--outline);
    letter-spacing: normal;
    text-transform: none;
}
.advanced-content {
    padding: 0.75rem 1rem 1rem;
}
.advanced-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 0.75rem;
}
.advanced-grid .field {
    margin-bottom: 0;
    min-width: 0;
}
.advanced-grid .field input[type="number"] {
    width: 100%;
    max-width: 100%;
    box-sizing: border-box;
}
.advanced-checkbox-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 0.75rem;
    align-items: center;
}
.advanced-checkbox-row .checkbox-field {
    margin-bottom: 0;
}
.advanced-subsection-title {
    font-family: var(--font-body);
    font-size: 15px;
    font-weight: 600;
    color: var(--on-surface);
    margin: 0 0 0.625rem 0;
    padding-bottom: 0.35rem;
    border-bottom: 1px solid var(--outline-variant);
    letter-spacing: normal;
    text-transform: none;
}
.advanced-grid + .advanced-subsection-title {
    margin-top: 1rem;
    padding-top: 0.35rem;
}
.advanced-grid + .field,
.advanced-checkbox-row + .field {
    margin-top: 1rem;
}

/* Filter section */
.filter-section {
    margin-top: 1rem;
    padding-top: 1rem;
}
.filter-section-title {
    font-family: var(--font-body);
    font-size: 13px;
    font-weight: 600;
    text-transform: none;
    letter-spacing: normal;
    color: var(--on-surface-variant);
    margin-bottom: 0.75rem;
}
.filter-section-desc {
    font-size: 13px;
    color: var(--on-surface-variant);
    margin-bottom: 0.75rem;
    margin-top: -0.5rem;
}
.notebook-hint {
    padding-left: 1.625rem;
    margin-top: -0.5rem;
}
.notebook-path-disabled {
    opacity: 0.5;
}

/* ── API key source radio ─────────────────────────────────────────── */
.api-key-source {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
}
.api-key-source-option {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 13px;
    color: var(--on-surface);
    cursor: pointer;
}
.api-key-source-option input[type="radio"] {
    accent-color: var(--primary);
    cursor: pointer;
}
.api-key-callout {
    background: var(--warning-container);
    border-left: 3px solid var(--warning);
    border-radius: var(--radius-sm);
    padding: 0.5rem 0.75rem;
    font-size: 13px;
    color: var(--on-surface);
    margin-top: 0.5rem;
    display: none;
}

/* ── Domino job link ──────────────────────────────────────────────── */
.domino-job-link-row {
    margin-bottom: 0.5rem;
}
.domino-job-link {
    font-size: 13px;
    font-weight: 600;
    color: var(--primary);
}

/* ── Primary Button ───────────────────────────────────────────────── */
button.primary {
    background: #543fde;
    border: 1px solid transparent;
    border-radius: var(--radius-sm);
    padding: 0 16px;
    height: 32px;
    color: #ffffff;
    font-family: var(--font-body);
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.15s ease;
    box-shadow: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    box-sizing: border-box;
}
button.primary:hover {
    background: #3b23d1;
    box-shadow: none;
}
button.primary:active {
    background: #311eae;
    box-shadow: none;
}
button.primary:disabled {
    opacity: 0.4;
    cursor: not-allowed;
}

/* ── Terminal Card ────────────────────────────────────────────────── */
.terminal-card {
    background: var(--surface-container-lowest);
    border: 1px solid var(--outline-variant);
    border-radius: var(--radius-sm);
    padding: 1rem 1.25rem;
    box-shadow: var(--shadow-sm);
}
.terminal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.75rem;
}
.terminal-header h3 {
    font-family: var(--font-headline);
    font-size: 13px;
    font-weight: 700;
}
.terminal-actions {
    display: flex;
    gap: 0.5rem;
}
.terminal-action {
    font-family: var(--font-body);
    font-size: 13px;
    font-weight: 500;
    color: #ffffff;
    text-decoration: none;
    cursor: pointer;
    padding: 0.375rem 0.875rem;
    border-radius: var(--radius-sm);
    background: #543fde;
    border: none;
    transition: background 0.15s ease;
    min-height: 32px;
    display: inline-flex;
    align-items: center;
}
.terminal-action:hover {
    background: #3b23d1;
    color: #ffffff;
}
.terminal-action-disabled {
    opacity: 0.35;
    pointer-events: none;
}

/* Status badges */
.terminal-status {
    display: inline-block;
    font-family: var(--font-body);
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 3px 10px;
    border-radius: var(--radius-sm);
    margin-bottom: 0.75rem;
}
.terminal-status-idle {
    background: var(--surface-container);
    color: var(--on-surface-variant);
}
.terminal-status-running {
    background: var(--secondary-container);
    color: var(--primary);
}
.terminal-status-completed {
    background: var(--success-container);
    color: var(--success);
}
.terminal-status-failed {
    background: var(--error-container);
    color: var(--on-surface);
}
.terminal-status-cancelled {
    background: var(--warning-container);
    color: var(--warning);
}
.terminal-status-queued {
    background: var(--warning-container);
    color: var(--warning);
}
.terminal-status-submitted {
    background: var(--secondary-container);
    color: var(--primary);
}
.terminal-status-succeeded {
    background: var(--success-container);
    color: var(--success);
}

/* ── Progress Phases ──────────────────────────────────────────────── */
.progress-phases {
    display: flex;
    gap: 0.375rem;
    margin-bottom: 0.75rem;
    padding: 0.625rem;
    background: var(--surface-container-low);
    border-radius: var(--radius-md);
}
.phase-item {
    flex: 1;
    min-width: 0;
}
.phase-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.3rem;
}
.phase-name {
    font-family: var(--font-body);
    font-size: 10px;
    font-weight: 700;
    color: var(--outline);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.phase-pct {
    font-size: 10px;
    color: var(--outline);
    font-family: var(--font-body);
    font-variant-numeric: tabular-nums;
}
.phase-check {
    color: var(--success);
    font-size: 10px;
}
.phase-bar {
    height: 3px;
    background: var(--surface-container-high);
    border-radius: 1px;
    overflow: hidden;
}
.phase-bar-fill {
    height: 100%;
    background: var(--primary);
    border-radius: 1px;
    transition: width 0.3s ease;
}
.phase-bar-complete .phase-bar-fill {
    background: var(--success);
}
@keyframes shimmer {
    0% { background-position: 100% center; }
    100% { background-position: 0% center; }
}
.phase-active .phase-name {
    background: linear-gradient(
        90deg,
        rgba(67, 67, 213, 0.5) 0%,
        rgba(67, 67, 213, 0.5) 40%,
        rgba(67, 67, 213, 1) 50%,
        rgba(67, 67, 213, 0.5) 60%,
        rgba(67, 67, 213, 0.5) 100%
    );
    background-size: 200% 100%;
    background-clip: text;
    -webkit-background-clip: text;
    color: transparent;
    animation: shimmer 2s linear infinite;
}
.phase-complete .phase-name {
    color: var(--success);
}
.phase-pending .phase-name {
    color: var(--surface-dim);
}

/* ── Dark Terminal Console ────────────────────────────────────────── */
.terminal {
    background: #0f172a;
    border-radius: 0 0 12px 12px;
    padding: 1rem;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 12px;
    line-height: 1.65;
    color: #cbd5e1;
    min-height: 0;
    max-height: 360px;
    overflow-y: auto;
    white-space: pre-wrap;
    margin-top: 0.5rem;
    box-shadow: 0 12px 40px rgba(15, 23, 42, 0.3);
}
.terminal-idle {
    min-height: 0;
    color: #475569;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--font-body);
    font-size: 13px;
    border-radius: 12px;
}
.terminal-line-active {
    color: #8888ff;
}
.terminal-line-complete {
    color: #4ADE80;
}
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
}
/* Only animate new log lines appended via JS, not on HTMX swap */
.log-line.new {
    animation: fadeIn 0.2s ease forwards;
}
/* Suppress transitions inside HTMX-swapped panels to prevent flicker */
#status-panel * ,
#job-history-content * {
    animation: none !important;
}

/* ── Download Buttons ─────────────────────────────────────────────── */
.download-section {
    display: flex;
    gap: 0.75rem;
    margin: 0.75rem 0;
    flex-wrap: wrap;
}
.download-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: var(--success);
    color: white;
    border-radius: var(--radius-sm);
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    text-decoration: none;
    transition: all 0.2s ease;
    box-shadow: var(--shadow-sm);
}
.download-btn:hover {
    filter: brightness(0.9);
    color: white;
    box-shadow: var(--shadow-md);
}
.download-btn::before {
    content: '\u2193';
    font-size: 1rem;
}
.download-btn-secondary {
    background: var(--surface-container-lowest);
    color: var(--success);
    border: 1.5px solid var(--success);
    box-shadow: none;
}
.download-btn-secondary:hover {
    background: rgba(40, 164, 100, 0.05);
    color: var(--success);
    filter: none;
}
.download-btn-secondary::before {
    content: '\u2193';
    font-size: 1rem;
}

/* ── Output Panel ─────────────────────────────────────────────────── */
.output-panel {
    flex: 1;
    min-height: 0;
    background: var(--surface-container-lowest);
    border: 1px solid var(--outline-variant);
    border-radius: var(--radius-sm);
    box-shadow: var(--shadow-sm);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    padding: 1rem;
}
/* ── Job History ──────────────────────────────────────────────────── */
#job-history-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
}
#job-history-content > .spec-file-empty {
    flex: 1;
    justify-content: center;
}
.job-history-section {
    margin-top: 1rem;
}
.job-history-section summary {
    font-family: var(--font-body);
    font-size: 13px;
    font-weight: 600;
    text-transform: none;
    letter-spacing: normal;
    color: var(--on-surface-variant);
    cursor: pointer;
    padding: 0.75rem 1rem;
    background: var(--surface-container-lowest);
    border: 1px solid var(--outline-variant);
    border-radius: var(--radius-sm);
    list-style: none;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.job-history-section summary::-webkit-details-marker { display: none; }
.job-history-section summary::before {
    content: '\u25B6';
    font-size: 8px;
    transition: transform 0.2s ease;
}
.job-history-section[open] summary::before { transform: rotate(90deg); }
.job-history-section[open] summary {
    border-radius: 4px 4px 0 0;
}
.job-history-content {
    background: var(--surface-container-lowest);
    border: 1px solid var(--outline-variant);
    border-top: none;
    border-radius: 0 0 var(--radius-sm) var(--radius-sm);
    padding: 1rem 1.25rem;
}
.spec-list-item-name {
    font-family: var(--font-body);
}
.history-table-wrap {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
}
.history-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    min-width: 560px;
}
.history-table th {
    text-align: left;
    font-family: var(--font-body);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--on-surface-variant);
    padding: 0 0.75rem 0.625rem 0;
    border-bottom: 1px solid var(--outline-variant);
    white-space: nowrap;
}
.history-table td {
    padding: 0.625rem 0.75rem 0.625rem 0;
    color: var(--on-surface);
    border-bottom: 1px solid var(--outline-variant);
    white-space: nowrap;
}
.history-table tr:last-child td { border-bottom: none; }
.history-status {
    display: inline-block;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: var(--radius-sm);
    text-transform: uppercase;
    letter-spacing: 0.03em;
}
.history-status-queued { background: var(--warning-container); color: var(--warning); }
.history-status-submitted { background: var(--secondary-container); color: var(--primary); }
.history-status-pending { background: var(--warning-container); color: var(--warning); }
.history-status-running { background: var(--secondary-container); color: var(--primary); }
.history-status-succeeded { background: var(--success-container); color: var(--success); }
.history-status-failed { background: var(--error-container); color: var(--on-surface); }
.history-status-cancelled { background: var(--warning-container); color: var(--warning); }
.history-toggle {
    font-size: 13px;
    font-weight: 500;
    color: var(--primary);
    cursor: pointer;
    padding: 0.375rem 0;
    margin-top: 0.25rem;
    list-style: none;
    user-select: none;
}
.history-toggle::-webkit-details-marker { display: none; }
.history-toggle::before {
    content: "\\25b6";
    display: inline-block;
    font-size: 0.5rem;
    margin-right: 0.375rem;
    transition: transform 0.15s ease;
    vertical-align: middle;
}
details[open] > .history-toggle::before {
    transform: rotate(90deg);
}
.history-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
    margin-top: 0.75rem;
}

/* ── Card Footer (Generate button) ────────────────────────────────── */
.card-footer {
    display: flex;
    justify-content: flex-start;
    align-items: center;
    gap: 0.75rem;
    padding-top: 1.25rem;
    padding-left: 1.5rem;
    padding-right: 1.5rem;
    margin-left: -1.5rem;
    margin-right: -1.5rem;
    border-top: 1px solid var(--outline-variant);
}
.studio-col-mid > .bp-card > .card-footer button.primary {
    flex: 1;
}

.section-divider {
    display: block;
    width: 100%;
    height: 0;
    margin: 0.75rem 0;
    padding: 0;
    border: none;
    border-top: 1px solid var(--ghost-border);
}

/* ── OR Divider ──────────────────────────────────────────────────── */
.or-divider {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.5rem 0;
}
.or-divider::before,
.or-divider::after {
    content: '';
    flex: 1;
    border-top: 1px solid rgba(199, 196, 215, 0.3);
}
.or-divider-text {
    font-family: var(--font-body);
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--outline);
}

select.hw-tier-select {
    width: 100%;
    max-width: 100%;
}
select.hw-tier-select option {
    font-size: 13px;
    line-height: 1.35;
    padding: 0.25rem 0;
}

/* ── Insight card ─────────────────────────────────────────────────── */
.insight-card {
    background: #ffffff;
    border: 1px solid var(--outline-variant);
    border-left: 3px solid var(--primary);
    border-radius: var(--radius-sm);
    padding: 1rem 1.25rem;
    margin-top: 1rem;
}
.insight-card h3 {
    font-family: var(--font-headline);
    font-size: 14px;
    font-weight: 700;
    color: var(--on-surface);
    margin-bottom: 0.25rem;
}
.insight-card p {
    font-size: 13px;
    line-height: 1.6;
    color: var(--on-surface-variant);
    margin: 0;
}

.app-link {
    color: var(--primary);
    font-size: 13px;
    font-weight: 500;
}

.app-link:hover {
    color: var(--primary-hover);
}

.header-version-text {
    margin: 0;
    color: var(--muted);
    font-size: 12px;
    font-family: ui-monospace, 'Cascadia Code', 'Source Code Pro', Menlo, monospace;
    font-variant-numeric: tabular-nums;
    letter-spacing: 0.02em;
    text-align: center;
}

.header-logs-link {
    color: var(--primary);
    font-size: 13px;
    font-weight: 600;
    text-decoration: none;
}

.header-logs-link:hover {
    color: var(--primary-hover);
    text-decoration: none;
}

.bootstrap-status-wrap,
.bootstrap-error-wrap {
    display: flex;
    justify-content: center;
}

.bootstrap-status-wrap {
    padding-top: 4rem;
}

.bootstrap-status-text {
    color: var(--on-surface-variant);
    font-size: 14px;
}

.bootstrap-error-wrap {
    padding-top: 2rem;
}

.bootstrap-error-card {
    background: var(--error-container);
    border: 1px solid rgba(194, 10, 41, 0.12);
    border-left: 3px solid var(--error);
    border-radius: var(--radius-sm);
    padding: 1.5rem;
    max-width: 640px;
    font-family: var(--font-body);
    box-shadow: var(--shadow-sm);
    color: var(--on-surface);
}

.bootstrap-error-detail {
    color: var(--on-surface);
    margin-top: 0.5rem;
}

.spec-file-list-empty {
    color: var(--outline);
    font-size: 13px;
}

.spec-selected-indicator {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    padding: 8px 0;
    font-size: 13px;
    gap: 6px;
}

.spec-selected-label {
    color: var(--outline);
}

#field-spec_path {
    white-space: nowrap;
    overflow-x: auto;
}

.lang-detection-row {
    display: none;
    padding: 8px 0;
    font-size: 13px;
    color: var(--on-surface-variant);
    align-items: center;
    flex-wrap: wrap;
    gap: 0.25rem;
}

.lang-detection-label,
.lang-detection-count {
    color: var(--outline);
}

.lang-detection-value {
    color: var(--on-surface);
    font-weight: 600;
}

.lang-override-btn {
    background: none;
    border: none;
    color: var(--primary);
    cursor: pointer;
    padding: 8px 12px;
    min-height: 44px;
    font-size: inherit;
    margin-left: 8px;
    border-radius: var(--radius-sm);
}

.lang-override-btn:hover {
    color: var(--primary-hover);
    background: rgba(84, 63, 222, 0.06);
}

.lang-override-select {
    display: none;
    border: 1px solid #d6d6d6;
    border-radius: 4px;
    padding: 0 2rem 0 14px;
    height: 36px;
    margin-left: 4px;
    font-size: 14px;
    font-family: var(--font-body);
    font-weight: 400;
    background: #ffffff;
    color: #2e2e38;
    -webkit-appearance: none;
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%2365657b' stroke-width='1.5' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 0.75rem center;
    cursor: pointer;
    outline: none;
    transition: border-color 0.15s ease;
}
.lang-override-select:hover,
.lang-override-select:focus {
    border-color: #543fde;
    box-shadow: none;
}

.warning-banner {
    padding: 0.625rem 1rem;
    border-radius: var(--radius-sm);
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    box-shadow: var(--shadow-sm);
}

.warning-banner-info {
    background: var(--info-container);
    border-left: 3px solid var(--info);
    color: var(--on-surface);
}

.warning-banner-warning {
    background: var(--warning-container);
    border-left: 3px solid var(--warning);
    color: var(--on-surface);
}

.warning-banner-error {
    background: var(--error-container);
    border-left: 3px solid var(--error);
    color: var(--on-surface);
}

.warning-banner-message {
    flex: 1;
    font-family: var(--font-body);
    font-size: 13px;
}

.warning-banner-close {
    display: flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.125rem;
    border-radius: var(--radius-sm);
    color: var(--on-surface-variant);
    flex-shrink: 0;
}
.warning-banner-close .material-symbols-outlined {
    font-size: 18px;
    line-height: 1;
}

.inline-callout {
    border-left: 3px solid;
    border-radius: var(--radius-sm);
    padding: 0.625rem 1rem;
    margin-bottom: 0.75rem;
    font-size: 13px;
    color: var(--on-surface);
    line-height: 1.5;
    font-family: var(--font-body);
}

.inline-callout-warning {
    background: var(--warning-container);
    border-left-color: var(--warning);
}

.spec-validation-success {
    color: var(--success);
    font-weight: 500;
    font-size: 13px;
}

.spec-validation-empty {
    color: var(--on-surface);
}

.spec-validation-pending {
    color: var(--outline);
    font-size: 13px;
}

.spec-validation-msg {
    color: var(--on-surface);
    font-size: 13px;
    margin-top: 6px;
}

.lang-empty-state {
    color: var(--outline);
}

/* ── Responsive ───────────────────────────────────────────────────── */

/* ═══════════════════════════════════════════════════════════════════
   WIZARD REDESIGN STYLES
   ═══════════════════════════════════════════════════════════════════ */

/* ── Page title row (project context) ────────────────────────────── */
.page-title-row {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
    flex-shrink: 0;
}
.page-title-text {
    font-family: var(--font-headline);
    font-size: 22px;
    font-weight: 700;
    color: var(--on-surface);
    letter-spacing: -0.02em;
}
.page-title-project {
    font-family: var(--font-body);
    font-size: 14px;
    font-weight: 400;
    color: var(--on-surface-variant);
}

/* ── Wizard step container ───────────────────────────────────────── */
.wizard-step {
    width: 100%;
    box-sizing: border-box;
    padding: 0 1.5rem;
}
.wizard-step-indicator {
    font-family: var(--font-body);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: var(--muted);
    margin-bottom: 0.35rem;
}

/* ── Wizard page: strip padding, set exact height, propagate via flex ── */
.page--wizard {
    padding: 0 !important;
    height: calc(100vh - 44px); /* 44px = domino-header */
    min-height: 0 !important;
    overflow: hidden;
}
/* Form propagates height down without pixel math */
.page--wizard > form {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
}

/* ── Wizard step 1: 2-row grid (columns | footer) ────────────────── */
#wizard-step1 {
    display: grid;
    grid-template-rows: 1fr auto;
    flex: 1;     /* fills the form's flex height */
    min-height: 0;
    overflow: hidden;
}

/* ── Wizard two-column layout (fills row 1) ──────────────────────── */
.wizard-layout {
    display: grid;
    grid-template-columns: minmax(340px, 5fr) minmax(320px, 6fr);
    gap: 0;
    overflow: hidden; /* clips both columns to the row height */
    min-height: 0;
}
.wizard-col-gallery {
    display: flex;
    flex-direction: column;
    gap: 0;
    padding: 1.5rem 1.5rem 1.5rem 1.5rem; /* replaces page padding removed by .page--wizard */
    overflow-y: auto;
}
.wizard-col-config {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    border-left: 1px solid var(--outline-variant);
    background: var(--surface); /* same as body — card provides the visual boundary */
    border-radius: 0 var(--radius-lg) var(--radius-lg) 0;
    padding: 1rem;
}
.preview-card {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    background: var(--surface-container-lowest);
    border: 1px solid var(--outline-variant);
    border-radius: var(--radius-sm);
    overflow: hidden;
    box-shadow: var(--shadow-sm);
    position: relative;
}
.preview-card-loading {
    position: absolute;
    inset: 0;
    display: none;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    color: var(--outline);
    text-align: center;
    background: color-mix(in srgb, var(--surface-container-lowest) 88%, transparent);
    backdrop-filter: blur(2px);
    z-index: 2;
}
.preview-card-loading.active {
    display: flex;
}

/* Edit template section */
.edit-tpl-section {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    flex-shrink: 0;
    padding: 0.875rem 1.25rem;
    border-top: 1px solid var(--outline-variant);
}
.edit-tpl-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.edit-tpl-maximize-btn {
    margin-left: auto;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    padding: 0;
    border: none;
    background: transparent;
    border-radius: var(--radius-sm);
    color: var(--on-surface-variant);
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
}
.edit-tpl-maximize-btn:hover {
    background: var(--surface-container-low);
    color: var(--primary);
}
.edit-tpl-maximize-icon {
    font-size: 16px;
    line-height: 1;
}
/* Maximized editor: hide preview panel, let edit section take its space.
   Output format stays visible at bottom. */
.preview-card.edit-maximized #template-preview-panel,
.preview-card.edit-maximized .preview-panel-header {
    display: none;
}
.preview-card.edit-maximized .edit-tpl-section {
    flex: 1 1 auto;
    border-top: none;
    min-height: 0;
}
.preview-card.edit-maximized .edit-tpl-textarea {
    flex: 1 1 auto;
    min-height: 0;
    height: 100%;
}
.edit-tpl-label {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--on-surface-variant);
}
.edit-tpl-textarea {
    font-family: 'SFMono-Regular', 'Consolas', 'Liberation Mono', 'Menlo', monospace;
    font-size: 12px;
    line-height: 1.6;
    color: var(--on-surface);
    background: var(--surface-container-lowest);
    border: 1px solid var(--outline-variant);
    border-radius: var(--radius-sm);
    padding: 0.75rem;
    resize: vertical;
    min-height: 180px;
    width: 100%;
    box-sizing: border-box;
    transition: border-color 0.15s;
    outline: none;
}
.edit-tpl-textarea:focus {
    border-color: var(--primary);
    box-shadow: 0 0 0 2px rgba(84, 63, 222, 0.12);
}
.edit-tpl-textarea::placeholder {
    color: var(--muted);
    font-style: italic;
}
.edit-tpl-actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.edit-tpl-action-btn {
    font-size: 12px;
    font-weight: 600;
    padding: 0.35rem 0.85rem;
    border-radius: var(--radius-sm);
    border: 1px solid var(--outline-variant);
    background: var(--surface-container-lowest);
    color: var(--on-surface);
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.edit-tpl-action-btn:hover:not(:disabled) {
    border-color: var(--primary);
    color: var(--primary);
}
.edit-tpl-action-btn:disabled {
    opacity: 0.55;
    cursor: not-allowed;
}
.edit-tpl-save-btn:not(:disabled) {
    background: var(--primary);
    color: var(--on-primary);
    border-color: var(--primary);
}
.edit-tpl-save-btn:not(:disabled):hover {
    background: color-mix(in srgb, var(--primary) 88%, black);
    color: var(--on-primary);
}
.edit-tpl-status {
    font-size: 12px;
    line-height: 1.4;
    min-height: 1.2em;
}
.edit-tpl-status.error {
    color: var(--error);
}
.edit-tpl-status.success {
    color: var(--success);
}

/* Output format section */
.output-fmt-section {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    flex-shrink: 0;
    padding: 0.875rem 1.25rem;
    border-top: 1px solid var(--outline-variant);
}
.output-fmt-label {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--on-surface-variant);
}
.output-fmt-group {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    gap: 0.4rem;
}
.output-fmt-option {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.25rem 0.6rem;
    border: 1.5px solid var(--outline-variant);
    border-radius: 999px;
    background: var(--surface-container-lowest);
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
    user-select: none;
    white-space: nowrap;
}
.output-fmt-option:has(.output-fmt-radio:checked) {
    border-color: var(--primary);
    background: var(--primary-fixed);
}
.output-fmt-option:hover {
    border-color: var(--primary);
    background: var(--primary-fixed);
}
.output-fmt-radio {
    accent-color: var(--primary);
    width: 13px;
    height: 13px;
    flex-shrink: 0;
    cursor: pointer;
}
.output-fmt-icon {
    font-size: 13px;
    color: var(--on-surface-variant);
}
.output-fmt-option:has(.output-fmt-radio:checked) .output-fmt-icon {
    color: var(--primary);
}
.output-fmt-text {
    font-size: 12px;
    font-weight: 500;
    color: var(--on-surface);
}
.wizard-col-title {
    font-size: 20px;
    font-weight: 700;
    color: var(--on-surface);
    letter-spacing: -0.015em;
    margin: 0;
}
@media (max-width: 900px) {
    #wizard-step1 {
        height: auto;
        overflow: visible;
    }
    .wizard-layout {
        grid-template-columns: 1fr;
        overflow: visible;
    }
    .wizard-col-config {
        height: auto;
        border-radius: 0 0 var(--radius-lg) var(--radius-lg);
        padding: 0.75rem;
    }
}

/* ── Gallery header row (title + Browse/Upload buttons) ────────── */
.gallery-header-row {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 0.75rem;
    margin-bottom: 1rem;
}
.gallery-action-btns {
    display: flex;
    gap: 0.5rem;
    flex-shrink: 0;
}
.gallery-action-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-family: var(--font-body);
    font-size: 12px;
    font-weight: 600;
    color: var(--on-surface-variant);
    background: transparent;
    border: 1px solid var(--outline-variant);
    border-radius: var(--radius-sm);
    padding: 0.3rem 0.7rem;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.gallery-action-btn:hover {
    background: var(--surface-container);
    border-color: var(--outline);
    color: var(--on-surface);
}

/* ── Advanced options accordion (below template cards) ──────────── */
.adv-opts-accordion {
    margin-top: 0.75rem;
    border: 1px solid var(--outline-variant);
    border-radius: var(--radius-md);
    background: var(--surface-container-lowest);
    overflow: hidden;
    flex-shrink: 0;
}
.adv-opts-accordion-summary {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.65rem 0.875rem;
    font-size: 13px;
    font-weight: 600;
    color: var(--on-surface-variant);
    cursor: pointer;
    list-style: none;
    user-select: none;
    transition: background 0.12s;
}
.adv-opts-accordion-summary::-webkit-details-marker { display: none; }
.adv-opts-accordion-summary::before {
    content: 'expand_more';
    font-family: 'Material Symbols Outlined';
    font-size: 16px;
    color: var(--muted);
    transition: transform 0.2s;
}
.adv-opts-accordion[open] .adv-opts-accordion-summary::before {
    transform: rotate(-180deg);
}
.adv-opts-accordion-summary:hover {
    background: var(--surface-container);
}
.adv-opts-accordion-body {
    border-top: 1px solid var(--outline-variant);
    padding: 1rem;
}

/* ── Filters accordion fields ────────────────────────────────────── */
.filters-body {
    display: flex;
    flex-direction: column;
    gap: 0.875rem;
}
.filter-field {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
}
.filter-label {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 13px;
    font-weight: 500;
    color: var(--on-surface);
}
.filter-info-icon {
    font-size: 14px !important;
    color: var(--muted);
    cursor: help;
}
.filter-input {
    width: 100%;
    box-sizing: border-box;
    height: 36px;
    padding: 0 0.75rem;
    font-family: var(--font-body);
    font-size: 13px;
    color: var(--on-surface);
    background: var(--surface-container-lowest);
    border: 1px solid var(--outline-variant);
    border-radius: var(--radius-sm);
    outline: none;
    transition: border-color 0.15s;
}
.filter-input:focus {
    border-color: var(--primary);
}
.filter-input::placeholder {
    color: var(--muted);
}
.filter-checkbox-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 13px;
    font-weight: 500;
    color: var(--on-surface);
    cursor: pointer;
    user-select: none;
}
.filter-checkbox {
    width: 16px;
    height: 16px;
    accent-color: var(--primary);
    cursor: pointer;
    flex-shrink: 0;
}

/* ── Uploaded/browsed spec confirmation bar ─────────────────────── */
.spec-confirm-bar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: color-mix(in srgb, var(--secondary) 8%, var(--surface));
    border: 1px solid color-mix(in srgb, var(--secondary) 25%, transparent);
    border-radius: var(--radius-sm);
    padding: 0.45rem 0.75rem;
    margin-bottom: 0.75rem;
    font-size: 13px;
}
.spec-confirm-icon {
    font-size: 16px !important;
    color: var(--secondary);
    flex-shrink: 0;
}
.spec-confirm-name {
    font-weight: 600;
    color: var(--on-surface);
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.spec-confirm-source {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--secondary);
    flex-shrink: 0;
}
.spec-confirm-remove {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: none;
    cursor: pointer;
    color: var(--muted);
    padding: 2px;
    border-radius: 4px;
    flex-shrink: 0;
    transition: background 0.15s, color 0.15s;
}
.spec-confirm-remove:hover {
    background: color-mix(in srgb, var(--error) 12%, transparent);
    color: var(--error);
}

/* ── Browse spec modal ───────────────────────────────────────────── */
.browse-modal {
    width: 560px;
    max-width: 95vw;
}
.browse-modal-body {
    padding: 0;
}
.browse-breadcrumb-bar {
    padding: 0.625rem 1rem;
    border-bottom: 1px solid var(--outline-variant);
    font-size: 12px;
}
.browse-crumb-link {
    font-size: 13px;
    font-weight: 500;
    color: var(--primary);
    text-decoration: none;
}
.browse-crumb-link:hover { text-decoration: underline; }
.browse-file-list {
    display: flex;
    flex-direction: column;
    max-height: 340px;
    overflow-y: auto;
    border: 1px solid var(--outline-variant);
    border-radius: var(--radius-md);
    margin: 0.875rem 1rem;
    overflow: hidden;
}
.browse-item {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    padding: 0.6rem 0.875rem;
    cursor: default;
    user-select: none;
    border-bottom: 1px solid var(--outline-variant);
    background: var(--surface-container-lowest);
    transition: background 0.1s;
}
.browse-item:last-child { border-bottom: none; }
.browse-item-file { cursor: pointer; }
.browse-item-file:hover { background: var(--surface-container-low); }
.browse-item-selected {
    background: color-mix(in srgb, var(--primary) 8%, var(--surface-container-lowest)) !important;
}
.browse-icon {
    font-size: 16px !important;
    flex-shrink: 0;
    font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 20;
}
.browse-icon-folder { color: var(--on-surface-variant); }
.browse-icon-yaml   { color: var(--on-surface-variant); }
.browse-item-name {
    font-size: 13px;
    font-weight: 400;
    color: var(--on-surface);
    flex: 1;
}
.browse-item-meta {
    font-size: 12px;
    color: var(--muted);
    flex-shrink: 0;
}
.browse-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 0.875rem 1.375rem;
    border-top: 1px solid var(--outline-variant);
    background: var(--surface-container-lowest);
    flex-shrink: 0;
}
.browse-selected-label {
    font-size: 12px;
    color: var(--on-surface-variant);
    flex: 1;
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    white-space: normal;
    font-style: italic;
}

/* ── Project context chip — Domino tag style ─────────────────────── */
.project-context-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    font-family: var(--font-body);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.01em;
    color: var(--secondary);
    background: var(--secondary-container);
    border-radius: 4px;
    padding: 2px 8px 2px 5px;
    margin-top: 0.3rem;
    white-space: nowrap;
}

/* ── Preview panel header ────────────────────────────────────────── */
.preview-panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.875rem 1.25rem;
    border-bottom: 1px solid var(--outline-variant);
    flex-shrink: 0;
}
.preview-panel-label {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--on-surface-variant);
}
.preview-panel-tag {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--secondary);
    background: color-mix(in srgb, var(--secondary) 12%, transparent);
    border: 1px solid color-mix(in srgb, var(--secondary) 30%, transparent);
    border-radius: 4px;
    padding: 1px 6px;
    line-height: 1.6;
}
.adv-opts-link {
    background: none;
    border: 1px solid var(--outline-variant);
    border-radius: var(--radius-sm);
    cursor: pointer;
    font-size: 12px;
    font-weight: 500;
    font-family: var(--font-body);
    color: var(--on-surface-variant);
    padding: 0.25rem 0.625rem;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.adv-opts-link:hover {
    background: var(--surface-container);
    border-color: var(--outline);
    color: var(--on-surface);
}

/* ── Footer: Advanced options (left) + Generate (right) ─────────── */
.wizard-footer {
    background: var(--surface-container-lowest);
    border-top: 1px solid var(--outline-variant);
    padding: 0.875rem 1.5rem;
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    flex-shrink: 0;
}
.wizard-footer-right {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

/* ── Template gallery (2-column card grid) ────────────────────────── */
.template-gallery {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.75rem;
}
@media (max-width: 640px) {
    .template-gallery {
        grid-template-columns: 1fr;
    }
}
.gallery-loading {
    grid-column: 1 / -1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 2rem;
    color: var(--outline);
}
.gallery-loading-icon {
    font-size: 2rem;
    color: var(--surface-dim);
    font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24;
}
.gallery-loading-text {
    font-size: 13px;
    color: var(--outline);
}

/* ── Template card ────────────────────────────────────────────────── */
.template-card {
    background: var(--surface-container-lowest);
    border: 1.5px solid var(--outline-variant);
    border-radius: var(--radius-sm);
    padding: 1rem;
    cursor: pointer;
    transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    box-shadow: var(--shadow-sm);
    user-select: none;
}
.template-card:hover {
    border-color: var(--primary);
    background: var(--primary-fixed);
    box-shadow: var(--shadow-md);
}
.template-card.selected {
    border-color: var(--primary);
    background: var(--primary-fixed);
    box-shadow: 0 0 0 2px rgba(84, 63, 222, 0.18);
}
.template-card.loading {
    pointer-events: none;
    opacity: 0.55;
    cursor: not-allowed;
}
.template-card.loading.selected {
    opacity: 0.85;
}
.template-card-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
/* .template-card-icon removed — icons no longer shown on cards */
.template-card-name {
    font-family: var(--font-headline);
    font-size: 13px;
    font-weight: 600;
    color: var(--on-surface);
    line-height: 1.3;
}
.template-card-desc {
    font-size: 12px;
    color: var(--on-surface-variant);
    line-height: 1.5;
    margin: 0;
}
.template-card-meta {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: auto;
}
.template-card-badge {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 2px 6px;
    border-radius: 2px;
    background: var(--surface-container);
    color: var(--on-surface-variant);
}
.template-card.selected .template-card-badge {
    background: rgba(84, 63, 222, 0.12);
    color: var(--primary);
}
.template-card-check {
    margin-left: auto;
    color: var(--primary);
    font-size: 1.1rem;
    display: none;
}
.template-card.selected .template-card-check {
    display: block;
}

/* ── "Or" divider ─────────────────────────────────────────────────── */
.or-divider-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}
.or-divider-line {
    flex: 1;
    height: 1px;
    background: var(--outline-variant);
}
.or-divider-row .or-divider-text {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--outline);
    white-space: nowrap;
}

/* ── Custom spec section ─────────────────────────────────────────── */
.custom-spec-section {
    margin-top: 0;
}
.custom-spec-actions {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding-top: 0.75rem;
}

/* ── Template preview panel ──────────────────────────────────────── */
.template-preview-panel {
    flex: 1 1 0;
    min-height: 200px;
    overflow-y: auto;
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
}
.preview-empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    color: var(--outline);
    text-align: center;
}
.preview-empty-icon {
    font-size: 2rem;
    color: var(--surface-dim);
    font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24;
}
.preview-empty-text {
    font-size: 13px;
    color: var(--outline);
}
.preview-yaml-pre {
    align-self: stretch;
    text-align: left;
    width: 100%;
    max-height: 100%;
    overflow: auto;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 11px;
    line-height: 1.4;
    margin: 0;
    padding: 0.75rem;
    background: var(--surface-container-low);
    border-radius: 8px;
    white-space: pre-wrap;
    word-break: break-word;
    color: var(--on-surface);
}
.preview-header {
    margin-bottom: 0.875rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid var(--outline-variant);
}
.preview-template-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--muted);
    margin-bottom: 0.25rem;
}
.preview-title {
    font-family: var(--font-headline);
    font-size: 16px;
    font-weight: 700;
    color: var(--on-surface);
    letter-spacing: -0.01em;
    margin-bottom: 0.25rem;
}
.preview-description {
    font-size: 12px;
    color: var(--on-surface-variant);
    line-height: 1.5;
}

.preview-sections {
    display: flex;
    flex-direction: column;
    gap: 2px;
}
.preview-section-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.35rem 0.5rem;
    border-radius: var(--radius-sm);
    background: var(--surface-container-low);
    font-size: 13px;
    color: var(--on-surface);
}
.preview-section-num {
    font-size: 10px;
    font-weight: 700;
    color: var(--muted);
    font-variant-numeric: tabular-nums;
    min-width: 1.4rem;
    text-align: right;
}
.preview-section-name {
    flex: 1;
}
.preview-section-badge {
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 1px 5px;
    border-radius: 2px;
    background: var(--secondary-container);
    color: var(--primary);
    flex-shrink: 0;
}

/* ── Wizard CTA area ─────────────────────────────────────────────── */
.wizard-cta-area {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}
.wizard-generate-btn {
    width: auto;
    height: 40px;
    font-size: 14px;
    font-weight: 600;
    border-radius: var(--radius-md);
    padding: 0 1.25rem;
    display: inline-flex;
    align-items: center;
    white-space: nowrap;
}
.wizard-error {
    font-size: 13px;
    color: var(--error);
    background: var(--error-container);
    border-left: 3px solid var(--error);
    border-radius: var(--radius-sm);
    padding: 0.5rem 0.75rem;
}


/* ── Step 2: Results ─────────────────────────────────────────────── */
.results-nav-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding-top: 1rem;
    margin-bottom: 1rem;
}
.back-link-btn {
    background: none;
    border: 1px solid var(--outline-variant);
    border-radius: var(--radius-sm);
    padding: 0.375rem 0.875rem;
    font-family: var(--font-body);
    font-size: 13px;
    font-weight: 500;
    color: var(--on-surface-variant);
    cursor: pointer;
    transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}
.back-link-btn:hover {
    background: var(--surface-container);
    color: var(--on-surface);
    border-color: var(--outline);
}
.results-panel {
    background: var(--surface-container-lowest);
    border: 1px solid var(--outline-variant);
    border-radius: var(--radius-sm);
    padding: 1.5rem;
    box-shadow: var(--shadow-sm);
    margin-bottom: 1rem;
    min-height: 200px;
}
.results-submitting {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    padding: 2rem;
    color: var(--outline);
}
.results-submitting-icon {
    font-size: 2.5rem;
    color: var(--primary);
    font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24;
    animation: spin-gentle 2s linear infinite;
}
@keyframes spin-gentle {
    0%   { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
.results-submitting-text {
    font-size: 14px;
    color: var(--on-surface-variant);
}

/* ── Results: active job card ────────────────────────────────────── */
.results-job-card {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}
.results-job-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
}
.results-job-info {}
.results-job-template {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--muted);
    margin-bottom: 0.25rem;
}
.results-job-title {
    font-family: var(--font-headline);
    font-size: 18px;
    font-weight: 700;
    color: var(--on-surface);
    letter-spacing: -0.01em;
}
.results-status-col {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.35rem;
}
.results-job-link {
    font-size: 12px;
    font-weight: 500;
    color: var(--primary);
}
.results-job-link:hover {
    color: var(--primary-hover);
}

/* ── Results: success state ──────────────────────────────────────── */
.results-success {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}
.results-success-banner {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    background: var(--success-container);
    border-radius: var(--radius-sm);
    padding: 1rem 1.25rem;
}
.results-success-icon {
    font-size: 1.75rem;
    color: var(--success);
    font-variation-settings: 'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24;
    flex-shrink: 0;
}
.results-success-text {
    flex: 1;
}
.results-success-headline {
    font-family: var(--font-headline);
    font-size: 15px;
    font-weight: 700;
    color: var(--success);
}
.success-open-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.4rem 1rem;
    background: #ffffff;
    color: var(--success);
    border: none;
    border-radius: var(--radius-sm);
    font-size: 13px;
    font-weight: 600;
    text-decoration: none;
    white-space: nowrap;
    flex-shrink: 0;
    transition: opacity 0.15s;
}
.success-open-btn:hover {
    opacity: 0.88;
    color: var(--success);
    text-decoration: none;
}

/* ── Single animated progress bar ────────────────────────────────── */
.job-progress-wrap {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}
.job-progress-track {
    height: 6px;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 3px;
    overflow: hidden;
}
.job-progress-fill {
    height: 100%;
    background: rgba(255, 255, 255, 0.8);
    border-radius: 3px;
    width: 5%;
    transition: width 1.5s ease;
}
.job-progress-fill.animating {
    animation: job-progress-advance 22s ease-out forwards;
}
@keyframes job-progress-advance {
    0%   { width: 5%; }
    18%  { width: 28%; }
    36%  { width: 52%; }
    60%  { width: 72%; }
    85%  { width: 87%; }
    100% { width: 90%; }
}
.job-progress-label {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.7);
    font-family: var(--font-body);
}

/* ── Doc preview ────────────────────────────────────────────────── */
.doc-preview-wrap {
    margin-top: 16px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    padding-top: 12px;
    max-height: 480px;
    overflow-y: auto;
}
.doc-preview-loading {
    display: flex;
    align-items: center;
    gap: 8px;
    color: rgba(255, 255, 255, 0.6);
    font-size: 13px;
    padding: 8px 0;
}
.doc-preview-spin {
    animation: spin 1.2s linear infinite;
    font-size: 18px;
}
.doc-preview-content {
    font-family: var(--font-body);
    font-size: 13px;
    color: var(--text-primary);
    line-height: 1.6;
}
.doc-preview-content h1, .doc-preview-content h2, .doc-preview-content h3 {
    margin: 12px 0 6px;
    font-weight: 600;
}
.doc-preview-content p { margin: 0 0 8px; }
.doc-preview-error {
    color: var(--status-failed);
    font-size: 12px;
    padding: 6px 0;
}

/* ── Landing page doc preview overlay ───────────────────────────── */
.landing-doc-preview {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
}
.landing-doc-preview-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px 8px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
}
.landing-doc-preview-title {
    font-weight: 600;
    font-size: 13px;
    color: var(--text-primary);
}
.landing-doc-preview-close {
    background: none;
    border: none;
    cursor: pointer;
    padding: 2px;
    color: var(--text-secondary);
    display: flex;
    align-items: center;
}
.landing-doc-preview-close:hover { color: var(--text-primary); }
.landing-doc-preview-body {
    flex: 1;
    overflow-y: auto;
    padding: 12px 14px;
}

/* ── Results: failed state ───────────────────────────────────────── */
.results-failed {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}
.results-failed-banner {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    background: var(--error-container);
    border-radius: var(--radius-sm);
    padding: 1rem 1.25rem;
}
.results-failed-icon {
    font-size: 1.75rem;
    color: var(--error);
    font-variation-settings: 'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24;
    flex-shrink: 0;
}
.results-failed-text {
    flex: 1;
}
.results-failed-headline {
    font-family: var(--font-headline);
    font-size: 15px;
    font-weight: 700;
    color: var(--error);
    margin-bottom: 0.15rem;
}
.results-failed-detail {
    font-size: 13px;
    color: var(--on-surface-variant);
}
.results-retry-btn {
    align-self: flex-start;
}

/* ── Results: running state ──────────────────────────────────────── */
.results-running {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}
.results-running-banner {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    background: var(--secondary-container);
    border-radius: var(--radius-sm);
    padding: 1rem 1.25rem;
}
.results-running-spinner {
    font-size: 1.75rem;
    color: var(--primary);
    font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
    animation: spin-gentle 1.5s linear infinite;
    flex-shrink: 0;
}
.results-running-headline {
    font-family: var(--font-headline);
    font-size: 15px;
    font-weight: 700;
    color: var(--primary);
    margin-bottom: 0.15rem;
}
.results-running-sub {
    font-size: 13px;
    color: var(--on-surface-variant);
}

/* ── History section (in Step 2) ─────────────────────────────────── */
.history-section {
    margin-top: 0;
    /* Override advanced-section overflow:hidden so the table can scroll */
    overflow: visible;
}

/* ── Layout switcher (top-right of Step 2 nav) ─────────────────────── */
.layout-switcher-slot { margin-left: auto; }
.history-btn-slot { }
.layout-switcher {
    display: inline-flex;
    align-items: center;
    background: var(--surface-container);
    border: 1px solid var(--outline-variant);
    border-radius: var(--radius-sm);
    overflow: hidden;
}
.layout-switcher-btn {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.3rem 0.55rem;
    font-size: 13px;
    color: var(--on-surface-variant);
    transition: background 0.15s, color 0.15s;
    line-height: 1;
    display: flex;
    align-items: center;
    gap: 0.3rem;
}
.layout-switcher-btn:hover { background: var(--surface-container-high); color: var(--on-surface); }
.layout-switcher-btn.active {
    background: var(--primary);
    color: var(--on-primary);
}
.layout-switcher-divider {
    width: 1px;
    height: 20px;
    background: var(--outline-variant);
}

/* ── History drawer button (Layout B) ──────────────────────────────── */
.history-drawer-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.3rem 0.65rem;
    font-size: 13px;
    font-weight: 500;
    color: var(--primary);
    background: var(--surface-container-low);
    border: 1px solid var(--outline-variant);
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
}
.history-drawer-btn:hover {
    background: var(--surface-container);
    border-color: var(--primary);
}
.history-drawer-btn .material-symbols-outlined { font-size: 16px; }

/* ── Advanced options modal ─────────────────────────────────────────── */
.modal-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.45);
    z-index: 300;
    align-items: center;
    justify-content: center;
}
.modal-overlay.open {
    display: flex;
}
.adv-opts-modal {
    background: var(--surface-container-lowest);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-lg);
    width: min(640px, 94vw);
    max-height: 86vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}
.modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 1.375rem;
    border-bottom: 1px solid var(--outline-variant);
    flex-shrink: 0;
    background: var(--surface-container-lowest);
}
.modal-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--on-surface);
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.modal-close-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: none;
    cursor: pointer;
    color: var(--on-surface-variant);
    padding: 0.25rem;
    border-radius: var(--radius-sm);
    width: 32px;
    height: 32px;
    transition: background 0.15s, color 0.15s;
}
.modal-close-btn .material-symbols-outlined {
    font-size: 20px;
    line-height: 1;
}
.modal-close-btn:hover { background: var(--surface-container); color: var(--on-surface); }
.modal-body {
    flex: 1;
    overflow-y: auto;
    padding: 1.375rem;
}
.modal-body > .advanced-content { padding: 0; } /* only strip top-level wrapper padding */
.modal-body .advanced-section { margin-top: 0.625rem; }
.modal-footer {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding: 0.875rem 1.375rem;
    border-top: 1px solid var(--outline-variant);
    flex-shrink: 0;
    background: var(--surface-container-lowest);
}

/* ── History drawer (Layout B) ─────────────────────────────────────── */
.history-drawer-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.25);
    z-index: 200;
}
.history-drawer-overlay.open { display: block; }

.history-drawer {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    width: min(520px, 92vw);
    background: var(--surface-container-lowest);
    border-left: 1px solid var(--outline-variant);
    box-shadow: var(--shadow-lg, -4px 0 24px rgba(0,0,0,0.12));
    z-index: 201;
    display: flex;
    flex-direction: column;
    transform: translateX(100%);
    transition: transform 0.25s cubic-bezier(0.4,0,0.2,1);
}
.history-drawer.open { transform: translateX(0); }

.drawer-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 1.25rem;
    border-bottom: 1px solid var(--outline-variant);
    background: var(--surface-container-lowest);
    flex-shrink: 0;
}
.drawer-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--on-surface);
}
.drawer-close-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: none;
    cursor: pointer;
    color: var(--on-surface-variant);
    padding: 0.25rem;
    border-radius: var(--radius-sm);
    width: 32px;
    height: 32px;
    transition: background 0.15s, color 0.15s;
}
.drawer-close-btn .material-symbols-outlined {
    font-size: 20px;
    line-height: 1;
}
.drawer-close-btn:hover { background: var(--surface-container); color: var(--on-surface); }

.drawer-body {
    flex: 1;
    overflow-y: auto;
    padding: 1.25rem;
}
.drawer-body .history-table-wrap { margin-top: 0; }
.drawer-body .history-actions { margin-top: 0.75rem; }

/* ── Layout B: success action links ────────────────────────────────── */
.success-action-links {
    display: flex;
    flex-wrap: wrap;
    gap: 0.625rem;
    margin-top: 1rem;
}
.success-action-link {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.4rem 0.875rem;
    font-size: 13px;
    font-weight: 500;
    border-radius: var(--radius-sm);
    text-decoration: none;
    transition: background 0.15s, border-color 0.15s;
    border: 1px solid var(--outline-variant);
    color: var(--primary);
    background: var(--surface-container-low);
}
.success-action-link:hover {
    background: var(--surface-container);
    border-color: var(--primary);
    text-decoration: none;
}
.success-action-link .material-symbols-outlined { font-size: 16px; }

/* ── Layout B: inline doc preview (no details wrapper) ─────────────── */
.doc-preview-inline {
    margin-top: 1.25rem;
    border: 1px solid var(--outline-variant);
    border-radius: var(--radius-md);
    overflow: hidden;
}
.doc-preview-inline-header {
    padding: 0.625rem 1rem;
    background: var(--surface-container-low);
    border-bottom: 1px solid var(--outline-variant);
    font-size: 13px;
    font-weight: 500;
    color: var(--on-surface-variant);
    display: flex;
    align-items: center;
    gap: 0.4rem;
}
.doc-preview-inline-header .material-symbols-outlined { font-size: 16px; }

/* ── History table: pending AutoDoc file cell ──────────────────────── */
.history-pending-cell {
    color: var(--on-surface-variant);
    font-style: italic;
    font-size: 12px;
}

/* ── Doc preview ──────────────────────────────────────────────────── */
.doc-preview-details {
    margin-top: 1rem;
    border: 1px solid var(--outline-variant);
    border-radius: var(--radius-md);
    overflow: hidden;
}
.doc-preview-summary {
    padding: 0.75rem 1rem;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    color: var(--primary);
    background: var(--surface-container-low);
    list-style: none;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    user-select: none;
}
.doc-preview-summary::before {
    content: '▶';
    font-size: 10px;
    transition: transform 0.2s ease;
}
.doc-preview-details[open] .doc-preview-summary::before {
    transform: rotate(90deg);
}
.preview-summary-link {
    margin-left: auto;
    font-size: 12px;
    font-weight: 400;
    color: var(--primary);
    text-decoration: none;
    padding: 0.1rem 0.3rem;
    border-radius: var(--radius-sm);
}
.preview-summary-link:hover { text-decoration: underline; }
.doc-preview-content {
    padding: 1.25rem 1.5rem;
    background: var(--surface-container-lowest);
    max-height: 60vh;
    overflow-y: auto;
}
.doc-preview-loading {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--on-surface-variant);
    font-size: 13px;
}
.doc-preview-error {
    color: var(--error);
    font-size: 13px;
    margin: 0;
}
.doc-preview-body {
    font-family: var(--font-body);
    font-size: 14px;
    line-height: 1.7;
    color: var(--on-surface);
}
.doc-preview-body h1 { font-size: 1.4rem; font-weight: 700; margin: 1.25rem 0 0.5rem; }
.doc-preview-body h2 { font-size: 1.15rem; font-weight: 600; margin: 1rem 0 0.4rem; }
.doc-preview-body h3 { font-size: 1rem; font-weight: 600; margin: 0.75rem 0 0.3rem; }
.doc-preview-body p  { margin: 0.4rem 0 0.75rem; }
.doc-preview-body table {
    border-collapse: collapse;
    width: 100%;
    margin: 0.75rem 0;
    font-size: 13px;
}
.doc-preview-body table th,
.doc-preview-body table td {
    border: 1px solid var(--outline-variant);
    padding: 0.4rem 0.6rem;
    text-align: left;
}
.doc-preview-body table th {
    background: var(--surface-container-low);
    font-weight: 600;
}
@keyframes spin { to { transform: rotate(360deg); } }
.rotating-icon { display: inline-block; animation: spin 1.2s linear infinite; }
"""
