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
    --warning: #cc8b00;
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
    background: #ffffff;
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
    box-sizing: border-box;
    flex-shrink: 0;
}
.domino-header-inner {
    width: 100%;
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
}
.studio-col-mid > .bp-card {
    display: flex;
    flex-direction: column;
}
.studio-col-mid > .bp-card > .card-footer {
    margin-top: auto;
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
    border-radius: var(--radius-lg);
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
    padding: 0.625rem 1.25rem;
    color: var(--primary);
    font-family: var(--font-body);
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.15s ease, color 0.15s ease;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    min-height: 36px;
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
    border-radius: 0px;
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
    padding: 0.625rem 1.25rem;
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
    min-height: 36px;
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
    background: #ebebeb;
    color: #65657b;
    cursor: not-allowed;
}

/* ── Terminal Card ────────────────────────────────────────────────── */
.terminal-card {
    background: var(--surface-container-lowest);
    border: 1px solid var(--outline-variant);
    border-radius: var(--radius-lg);
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
    border-radius: 0px;
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
    border-radius: 2px;
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
    border-radius: var(--radius-lg);
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
    min-width: 420px;
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
    max-width: 120px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.history-table tr:last-child td { border-bottom: none; }
.history-status {
    display: inline-block;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 0px;
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
    justify-content: stretch;
    padding-top: 1.25rem;
    margin-top: 0.75rem;
    border-top: 1px solid var(--outline-variant);
}
.card-footer button.primary {
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
    background: var(--surface-container-lowest);
    border-left: 3px solid var(--primary);
    border: 1px solid var(--outline-variant);
    border-left: 3px solid var(--primary);
    border-radius: var(--radius-md);
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
    background: none;
    border: none;
    font-size: 1.2rem;
    cursor: pointer;
    padding: 0 0.5rem;
    color: var(--on-surface-variant);
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
"""
