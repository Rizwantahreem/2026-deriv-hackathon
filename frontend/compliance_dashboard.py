"""
Compliance Dashboard — Internal tool for Deriv's KYC compliance team.

Provides:
- Submissions queue with status filtering
- Manual review panel (side-by-side form vs OCR data)
- Risk flag alerts
- Analytics summary (approval rates, country breakdown, avg scores)
"""

import streamlit as st
import time
from typing import Optional


# ============================================================================
# COUNTRY / DOC TYPE DISPLAY HELPERS
# ============================================================================

COUNTRY_LABELS = {"PK": "Pakistan", "GB": "United Kingdom", "AE": "UAE", "IN": "India"}
DOC_LABELS = {
    "cnic": "CNIC", "passport": "Passport", "driving_license": "Driving License",
    "utility_bill": "Utility Bill", "aadhaar": "Aadhaar", "emirates_id": "Emirates ID",
}


def _country(code):
    return COUNTRY_LABELS.get(code, code)


def _doc(dtype):
    return DOC_LABELS.get(dtype, dtype.replace("_", " ").title())


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def render_compliance_dashboard(submission_manager):
    """Render the full compliance dashboard."""

    # ── Inject dashboard-specific styles ──
    st.markdown("""
    <style>
        /* ── Stat cards ── */
        .dash-card {
            background: linear-gradient(135deg, #141928 0%, #1a2035 100%);
            border: 1px solid #2a3050;
            border-radius: 12px;
            padding: 20px 16px;
            text-align: center;
            transition: transform 0.15s;
        }
        .dash-card:hover { transform: translateY(-2px); }
        .dash-card .val {
            font-size: 2rem; font-weight: 700; margin: 0; line-height: 1.2;
        }
        .dash-card .lbl {
            font-size: 0.78rem; color: #8892a4; margin: 6px 0 0; text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* colour accents */
        .val-primary { color: #ff444f; }
        .val-green   { color: #00d084; }
        .val-red     { color: #ff4d6a; }
        .val-amber   { color: #ffb347; }
        .val-blue    { color: #4da6ff; }
        .val-white   { color: #e8ecf1; }

        /* ── Submission row card ── */
        .sub-card {
            background: #141928;
            border: 1px solid #232b40;
            border-radius: 10px;
            padding: 16px 20px;
            margin: 8px 0;
        }
        .sub-card-header {
            display: flex; justify-content: space-between; align-items: center;
            flex-wrap: wrap; gap: 8px;
        }
        .sub-card-header .doc-id {
            font-weight: 600; color: #e0e4eb; font-size: 0.95rem;
        }
        .badge {
            display: inline-block; padding: 3px 10px; border-radius: 20px;
            font-size: 0.72rem; font-weight: 600; text-transform: uppercase;
            letter-spacing: 0.4px;
        }
        .badge-accepted  { background: #0d3a25; color: #00d084; border: 1px solid #00d084; }
        .badge-rejected  { background: #3a0d18; color: #ff4d6a; border: 1px solid #ff4d6a; }
        .badge-review    { background: #3a2e0d; color: #ffb347; border: 1px solid #ffb347; }
        .badge-pending   { background: #1e2235; color: #8892a4; border: 1px solid #8892a4; }

        .badge-risk-high   { background: #3a0d18; color: #ff4d6a; }
        .badge-risk-medium { background: #3a2e0d; color: #ffb347; }
        .badge-risk-low    { background: #0d3a25; color: #00d084; }

        /* ── Progress bars for analytics ── */
        .bar-container {
            background: #1a2035; border-radius: 6px; overflow: hidden;
            height: 24px; margin: 4px 0 10px;
        }
        .bar-fill {
            height: 100%; border-radius: 6px;
            display: flex; align-items: center; padding-left: 8px;
            font-size: 0.75rem; font-weight: 600; color: #fff;
            min-width: 32px;
        }

        /* ── Compare table ── */
        .cmp-table { width: 100%; border-collapse: collapse; margin: 8px 0; }
        .cmp-table th {
            text-align: left; padding: 8px 12px; font-size: 0.78rem;
            color: #8892a4; border-bottom: 1px solid #2a3050;
            text-transform: uppercase; letter-spacing: 0.4px;
        }
        .cmp-table td {
            padding: 8px 12px; border-bottom: 1px solid #1e2538;
            font-size: 0.88rem; color: #d0d5de;
        }
        .cmp-mismatch { color: #ff4d6a !important; font-weight: 600; }
        .cmp-match    { color: #00d084 !important; }

        /* ── Section headers ── */
        .dash-section {
            font-size: 1.1rem; font-weight: 600; color: #e0e4eb;
            margin: 24px 0 12px; padding-bottom: 8px;
            border-bottom: 2px solid #ff444f;
        }
    </style>
    """, unsafe_allow_html=True)

    # ── Header ──
    st.markdown("""
    <div style="text-align:center; margin-bottom:24px;">
        <h1 style="color:#ff444f; margin:0; font-size:1.8rem;">Compliance Dashboard</h1>
        <p style="color:#8892a4; margin:4px 0 0; font-size:0.9rem;">Internal KYC Review &amp; Risk Management</p>
    </div>
    """, unsafe_allow_html=True)

    # Get data
    analytics = submission_manager.get_analytics()
    all_subs = submission_manager.get_all_submissions()
    pending = submission_manager.get_pending_reviews()
    flagged = submission_manager.get_flagged_submissions()

    # ================================================================
    # TOP STATS ROW
    # ================================================================
    cols = st.columns(5)
    stats = [
        (analytics["total"], "Total", "val-white"),
        (analytics["accepted"], "Accepted", "val-green"),
        (analytics["rejected"], "Rejected", "val-red"),
        (analytics["pending_review"], "Pending Review", "val-amber"),
        (analytics["high_risk_count"], "High Risk", "val-red"),
    ]
    for col, (val, lbl, cls) in zip(cols, stats):
        with col:
            st.markdown(f"""
            <div class="dash-card">
                <p class="val {cls}">{val}</p>
                <p class="lbl">{lbl}</p>
            </div>
            """, unsafe_allow_html=True)

    # Score row
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="dash-card">
            <p class="val val-blue">{analytics['avg_quality_score']}</p>
            <p class="lbl">Avg Quality Score</p>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="dash-card">
            <p class="val val-amber">{analytics['avg_risk_score']}</p>
            <p class="lbl">Avg Risk Score</p>
        </div>""", unsafe_allow_html=True)
    with c3:
        total = analytics["total"] or 1
        rate = (analytics["accepted"] / total) * 100
        st.markdown(f"""
        <div class="dash-card">
            <p class="val val-green">{rate:.0f}%</p>
            <p class="lbl">Approval Rate</p>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ================================================================
    # TABS
    # ================================================================
    tab1, tab2, tab3, tab4 = st.tabs([
        f"Submissions Queue ({analytics['total']})",
        f"Manual Review ({len(pending)})",
        f"Risk Alerts ({len(flagged)})",
        "Analytics"
    ])

    with tab1:
        _render_submissions_queue(all_subs)
    with tab2:
        _render_manual_review(pending, submission_manager)
    with tab3:
        _render_risk_alerts(flagged)
    with tab4:
        _render_analytics(analytics, all_subs)


# ============================================================================
# TAB 1 — SUBMISSIONS QUEUE
# ============================================================================

def _status_badge(status_val):
    m = {
        "accepted": ("Accepted", "badge-accepted"),
        "rejected": ("Rejected", "badge-rejected"),
        "needs_review": ("Needs Review", "badge-review"),
        "pending": ("Pending", "badge-pending"),
    }
    label, cls = m.get(status_val, (status_val, "badge-pending"))
    return f'<span class="badge {cls}">{label}</span>'


def _risk_badge(level):
    m = {
        "HIGH": ("High Risk", "badge-risk-high"),
        "MEDIUM": ("Medium", "badge-risk-medium"),
        "LOW": ("Low", "badge-risk-low"),
    }
    label, cls = m.get(level, (level, "badge-risk-low"))
    return f'<span class="badge {cls}">{label}</span>'


def _render_submissions_queue(submissions):
    if not submissions:
        st.info("No submissions yet.")
        return

    status_filter = st.selectbox(
        "Filter by status",
        ["All", "accepted", "needs_review", "rejected", "pending"],
        key="queue_filter",
        format_func=lambda x: x.replace("_", " ").title(),
    )

    filtered = submissions
    if status_filter != "All":
        from backend.deriv_api import DerivStatus
        status_map = {
            "accepted": DerivStatus.ACCEPTED,
            "needs_review": DerivStatus.NEEDS_REVIEW,
            "rejected": DerivStatus.REJECTED,
            "pending": DerivStatus.PENDING,
        }
        target = status_map.get(status_filter)
        if target:
            filtered = [s for s in submissions if s.status == target]

    for sub in reversed(filtered):
        st.markdown(f"""
        <div class="sub-card">
            <div class="sub-card-header">
                <span class="doc-id">{sub.document_id}</span>
                <span>{_status_badge(sub.status.value)} {_risk_badge(sub.risk_level)}</span>
            </div>
            <div style="display:flex; gap:24px; margin-top:10px; flex-wrap:wrap;">
                <span style="color:#8892a4; font-size:0.85rem;">
                    <strong style="color:#d0d5de;">{_doc(sub.document_type)}</strong> ({sub.side})
                </span>
                <span style="color:#8892a4; font-size:0.85rem;">
                    {_country(sub.country_code)}
                </span>
                <span style="color:#8892a4; font-size:0.85rem;">
                    Quality: <strong style="color:{'#00d084' if sub.quality_score >= 70 else '#ffb347' if sub.quality_score >= 50 else '#ff4d6a'}">{sub.quality_score}/100</strong>
                </span>
                <span style="color:#8892a4; font-size:0.85rem;">
                    Risk: <strong style="color:{'#ff4d6a' if sub.risk_score >= 50 else '#ffb347' if sub.risk_score >= 30 else '#00d084'}">{sub.risk_score}/100</strong>
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Expandable details
        with st.expander("View Details", expanded=False):
            if sub.risk_factors:
                st.markdown("**Risk Factors:**")
                for rf in sub.risk_factors:
                    sev = rf.get("severity", "low")
                    color = {"high": "#ff4d6a", "medium": "#ffb347", "low": "#00d084"}.get(sev, "#8892a4")
                    st.markdown(
                        f'- <span style="color:{color}; font-weight:600;">{rf.get("factor", "unknown").replace("_", " ").title()}</span>: {rf.get("detail", "")}',
                        unsafe_allow_html=True,
                    )
            if sub.mismatches:
                st.markdown("**Data Mismatches:**")
                for m in sub.mismatches:
                    st.markdown(
                        f'- **{m.get("field", "?").replace("_", " ").title()}**: '
                        f'Form `{m.get("form_value", "?")}` vs Document `{m.get("document_value", "?")}`'
                    )
            if sub.reviewer_action:
                st.markdown(f"**Reviewer Decision:** {sub.reviewer_action.title()}")
                if sub.reviewer_notes:
                    st.markdown(f"**Notes:** {sub.reviewer_notes}")


# ============================================================================
# TAB 2 — MANUAL REVIEW
# ============================================================================

def _render_manual_review(pending, submission_manager):
    if not pending:
        st.markdown("""
        <div class="dash-card" style="text-align:center; padding:40px;">
            <p class="val val-green" style="font-size:1.4rem;">All Clear</p>
            <p class="lbl">No submissions pending manual review</p>
        </div>
        """, unsafe_allow_html=True)
        return

    st.markdown(f"""
    <div style="background:#3a2e0d; border:1px solid #ffb347; border-radius:10px; padding:12px 18px; margin-bottom:16px;">
        <span style="color:#ffb347; font-weight:600;">{len(pending)} submission(s) require your review</span>
    </div>
    """, unsafe_allow_html=True)

    for i, sub in enumerate(pending):
        st.markdown(f'<div class="dash-section">{sub.document_id} — {_doc(sub.document_type)} ({_country(sub.country_code)})</div>', unsafe_allow_html=True)

        # Side-by-side comparison table
        form_fields = {k: v for k, v in (sub.form_data or {}).items() if v and str(v).lower() not in ("none", "")}
        ocr_fields = {k: v for k, v in (sub.ocr_data or {}).items() if v and str(v).lower() not in ("none", "null", "")}
        mismatch_fields = {m.get("field") for m in (sub.mismatches or [])}

        # Build unified field list
        all_keys = list(dict.fromkeys(list(form_fields.keys()) + list(ocr_fields.keys())))

        rows = ""
        for k in all_keys:
            fv = form_fields.get(k, "—")
            ov = ocr_fields.get(k, "—")
            is_mm = k in mismatch_fields
            cls = "cmp-mismatch" if is_mm else ""
            label = k.replace("_", " ").title()
            rows += f'<tr><td>{label}</td><td class="{cls}">{fv}</td><td class="{cls}">{ov}</td></tr>'

        st.markdown(f"""
        <table class="cmp-table">
            <thead><tr><th>Field</th><th>Form Data</th><th>Document (OCR)</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
        """, unsafe_allow_html=True)

        if sub.mismatches:
            for m in sub.mismatches:
                st.markdown(
                    f'<div style="background:#3a0d18; border-left:3px solid #ff4d6a; padding:8px 14px; margin:6px 0; border-radius:4px; font-size:0.88rem;">'
                    f'<strong style="color:#ff4d6a;">{m.get("field", "?").replace("_", " ").title()}</strong>: {m.get("message", "Mismatch detected")}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # Risk badge
        risk_colors = {"HIGH": "#ff4d6a", "MEDIUM": "#ffb347", "LOW": "#00d084"}
        st.markdown(
            f'<div style="margin:10px 0;"><span style="color:{risk_colors.get(sub.risk_level, "#8892a4")}; font-weight:600;">Risk: {sub.risk_level} ({sub.risk_score}/100)</span></div>',
            unsafe_allow_html=True,
        )

        # Action buttons
        col_a, col_b, col_c = st.columns([1, 1, 2])
        with col_a:
            if st.button("Approve", key=f"approve_{sub.document_id}_{i}", type="primary"):
                submission_manager.review_submission(sub.document_id, "approve", "Manually approved by compliance officer")
                st.rerun()
        with col_b:
            if st.button("Reject", key=f"reject_{sub.document_id}_{i}"):
                submission_manager.review_submission(sub.document_id, "reject", "Rejected during manual review")
                st.rerun()
        with col_c:
            st.text_input("Notes", key=f"notes_{sub.document_id}_{i}", placeholder="Optional reviewer notes...")

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)


# ============================================================================
# TAB 3 — RISK ALERTS
# ============================================================================

def _render_risk_alerts(flagged):
    if not flagged:
        st.markdown("""
        <div class="dash-card" style="text-align:center; padding:40px;">
            <p class="val val-green" style="font-size:1.4rem;">No Alerts</p>
            <p class="lbl">No high-risk submissions detected</p>
        </div>
        """, unsafe_allow_html=True)
        return

    # Sort by risk score descending
    flagged_sorted = sorted(flagged, key=lambda s: s.risk_score, reverse=True)

    for sub in flagged_sorted:
        risk_color = {"HIGH": "#ff4d6a", "MEDIUM": "#ffb347"}.get(sub.risk_level, "#ffb347")
        border = f"border-left: 4px solid {risk_color}"

        st.markdown(f"""
        <div class="sub-card" style="{border}">
            <div class="sub-card-header">
                <span class="doc-id">{sub.document_id}</span>
                <span>{_risk_badge(sub.risk_level)} {_status_badge(sub.status.value)}</span>
            </div>
            <div style="display:flex; gap:24px; margin-top:8px; flex-wrap:wrap;">
                <span style="color:#8892a4; font-size:0.85rem;">{_doc(sub.document_type)} — {_country(sub.country_code)}</span>
                <span style="color:#8892a4; font-size:0.85rem;">Quality: <strong>{sub.quality_score}/100</strong></span>
                <span style="color:{risk_color}; font-size:0.85rem; font-weight:600;">Risk Score: {sub.risk_score}/100</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("View Risk Details"):
            if sub.risk_factors:
                for rf in sub.risk_factors:
                    sev = rf.get("severity", "low")
                    color = {"high": "#ff4d6a", "medium": "#ffb347", "low": "#00d084"}.get(sev, "#8892a4")
                    st.markdown(
                        f'<div style="background:#141928; border-left:3px solid {color}; padding:8px 14px; margin:6px 0; border-radius:4px;">'
                        f'<strong style="color:{color}">{rf.get("factor", "").replace("_", " ").title()}</strong>: {rf.get("detail", "")}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            if sub.mismatches:
                st.markdown("**Data Mismatches:**")
                for m in sub.mismatches:
                    st.markdown(
                        f'- **{m.get("field", "?").replace("_", " ").title()}**: '
                        f'`{m.get("form_value", "?")}` vs `{m.get("document_value", "?")}`'
                    )


# ============================================================================
# TAB 4 — ANALYTICS
# ============================================================================

def _bar(label, value, total, color):
    pct = (value / total * 100) if total > 0 else 0
    return f"""
    <div style="margin-bottom:4px;">
        <div style="display:flex; justify-content:space-between; font-size:0.82rem; color:#d0d5de;">
            <span>{label}</span><span style="color:#8892a4">{value} ({pct:.0f}%)</span>
        </div>
        <div class="bar-container">
            <div class="bar-fill" style="width:{max(pct, 4)}%; background:{color};">{value}</div>
        </div>
    </div>
    """


def _render_analytics(analytics, all_subs):
    if not all_subs:
        st.info("No data to display yet.")
        return

    total = analytics["total"] or 1

    # ── Rates ──
    st.markdown('<div class="dash-section">Approval Breakdown</div>', unsafe_allow_html=True)

    accepted = analytics["accepted"]
    rejected = analytics["rejected"]
    review = analytics["pending_review"]

    st.markdown(
        _bar("Accepted", accepted, total, "#00d084")
        + _bar("Needs Review", review, total, "#ffb347")
        + _bar("Rejected", rejected, total, "#ff4d6a"),
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── By Country ──
    st.markdown('<div class="dash-section">By Country</div>', unsafe_allow_html=True)
    country_colors = {"PK": "#00d084", "GB": "#4da6ff", "AE": "#ffb347", "IN": "#ff4d6a"}
    bars = ""
    for code, count in analytics.get("by_country", {}).items():
        bars += _bar(_country(code), count, total, country_colors.get(code, "#8892a4"))
    st.markdown(bars, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── By Document Type ──
    st.markdown('<div class="dash-section">By Document Type</div>', unsafe_allow_html=True)
    doc_colors = {"cnic": "#ff444f", "passport": "#4da6ff", "driving_license": "#00d084",
                  "utility_bill": "#ffb347", "aadhaar": "#c471ed", "emirates_id": "#ffd700"}
    bars = ""
    for dtype, count in analytics.get("by_doc_type", {}).items():
        bars += _bar(_doc(dtype), count, total, doc_colors.get(dtype, "#8892a4"))
    st.markdown(bars, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Risk Distribution ──
    st.markdown('<div class="dash-section">Risk Distribution</div>', unsafe_allow_html=True)
    high = sum(1 for s in all_subs if s.risk_level == "HIGH")
    medium = sum(1 for s in all_subs if s.risk_level == "MEDIUM")
    low = sum(1 for s in all_subs if s.risk_level == "LOW")
    st.markdown(
        _bar("High Risk", high, total, "#ff4d6a")
        + _bar("Medium Risk", medium, total, "#ffb347")
        + _bar("Low Risk", low, total, "#00d084"),
        unsafe_allow_html=True,
    )

    # ── Score summary cards ──
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class="dash-card">
            <p class="val val-blue">{analytics['avg_quality_score']}/100</p>
            <p class="lbl">Average Quality Score</p>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="dash-card">
            <p class="val val-amber">{analytics['avg_risk_score']}/100</p>
            <p class="lbl">Average Risk Score</p>
        </div>""", unsafe_allow_html=True)
