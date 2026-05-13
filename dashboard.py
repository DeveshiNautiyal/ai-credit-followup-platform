"""
Finance Credit Follow-Up Email Agent — Dashboard
Travel Corporation India Ltd · AI Enablement Internship · Task 2
"""

import streamlit as st
import pandas as pd
import sqlite3
import json
import os
from datetime import datetime
from agent import run_agent, get_stage

# ══════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════

st.set_page_config(
    page_title="Credit Follow-Up Agent · TCI",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ══════════════════════════════════════════════
#  CUSTOM CSS — Dark luxury finance aesthetic
# ══════════════════════════════════════════════

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

/* ── Root & Background ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}
.stApp {
    background: #080C14;
    color: #E8EAF0;
}
section[data-testid="stSidebar"] {
    background: #0D1420 !important;
    border-right: 1px solid #1E2840;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }

/* ── Hero banner ── */
.hero {
    background: linear-gradient(135deg, #0D1420 0%, #111827 40%, #0A1628 100%);
    border: 1px solid #1E3050;
    border-radius: 16px;
    padding: 36px 40px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 240px; height: 240px;
    background: radial-gradient(circle, rgba(212,175,55,0.12) 0%, transparent 70%);
    border-radius: 50%;
}
.hero::after {
    content: '';
    position: absolute;
    bottom: -40px; left: 200px;
    width: 160px; height: 160px;
    background: radial-gradient(circle, rgba(59,130,246,0.08) 0%, transparent 70%);
    border-radius: 50%;
}
.hero-tag {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    letter-spacing: 3px;
    color: #D4AF37;
    text-transform: uppercase;
    margin-bottom: 10px;
}
.hero-title {
    font-family: 'Playfair Display', serif;
    font-size: 36px;
    font-weight: 900;
    color: #F0F4FF;
    line-height: 1.1;
    margin: 0 0 8px 0;
}
.hero-title span { color: #D4AF37; }
.hero-sub {
    font-size: 14px;
    color: #6B7A9A;
    margin: 0;
}

/* ── Metric cards ── */
.metric-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 28px;
}
.metric-card {
    background: #0D1420;
    border: 1px solid #1E2840;
    border-radius: 12px;
    padding: 20px 24px;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
}
.metric-card:hover { border-color: #D4AF37; }
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
}
.metric-card.gold::before  { background: linear-gradient(90deg, #D4AF37, #F4D03F); }
.metric-card.blue::before  { background: linear-gradient(90deg, #3B82F6, #60A5FA); }
.metric-card.green::before { background: linear-gradient(90deg, #10B981, #34D399); }
.metric-card.red::before   { background: linear-gradient(90deg, #EF4444, #F87171); }
.metric-label {
    font-size: 11px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #4B5A7A;
    margin-bottom: 8px;
    font-family: 'DM Mono', monospace;
}
.metric-value {
    font-family: 'Playfair Display', serif;
    font-size: 32px;
    font-weight: 700;
    color: #F0F4FF;
    line-height: 1;
}
.metric-sub {
    font-size: 12px;
    color: #4B5A7A;
    margin-top: 6px;
}

/* ── Section headers ── */
.section-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 28px 0 16px 0;
    padding-bottom: 12px;
    border-bottom: 1px solid #1E2840;
}
.section-header h2 {
    font-family: 'Playfair Display', serif;
    font-size: 20px;
    font-weight: 700;
    color: #F0F4FF;
    margin: 0;
}
.section-badge {
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    letter-spacing: 1px;
    padding: 3px 8px;
    border-radius: 4px;
    background: #1E2840;
    color: #6B7A9A;
    text-transform: uppercase;
}

/* ── Stage pills ── */
.stage-pill {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    font-family: 'DM Mono', monospace;
    letter-spacing: 0.5px;
}
.stage-1 { background: #052E16; color: #4ADE80; border: 1px solid #166534; }
.stage-2 { background: #0C1A4A; color: #60A5FA; border: 1px solid #1E40AF; }
.stage-3 { background: #2D1B00; color: #FBBF24; border: 1px solid #92400E; }
.stage-4 { background: #2D0A0A; color: #F87171; border: 1px solid #991B1B; }
.stage-5 { background: #1F0A3C; color: #C084FC; border: 1px solid #6B21A8; }

/* ── Email card ── */
.email-card {
    background: #0D1420;
    border: 1px solid #1E2840;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 12px;
    transition: border-color 0.2s, transform 0.2s;
}
.email-card:hover {
    border-color: #2E4070;
    transform: translateY(-1px);
}
.email-invoice {
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    color: #D4AF37;
    margin-bottom: 6px;
}
.email-subject {
    font-size: 15px;
    font-weight: 600;
    color: #E8EAF0;
    margin-bottom: 12px;
}
.email-body {
    font-size: 13px;
    color: #6B7A9A;
    white-space: pre-wrap;
    line-height: 1.6;
    border-left: 2px solid #1E2840;
    padding-left: 14px;
}
.escalation-card {
    background: #1A0A20;
    border: 1px solid #6B21A8;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
}
.escalation-label {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: #C084FC;
    letter-spacing: 1px;
    margin-bottom: 4px;
}

/* ── Sidebar ── */
.sidebar-logo {
    font-family: 'Playfair Display', serif;
    font-size: 18px;
    font-weight: 700;
    color: #D4AF37;
    padding: 0 0 20px 0;
    border-bottom: 1px solid #1E2840;
    margin-bottom: 20px;
}
.sidebar-logo span { color: #6B7A9A; font-size: 11px; font-family: 'DM Sans', sans-serif; display: block; margin-top: 2px; font-weight: 300; }

/* ── Run button ── */
.stButton > button {
    background: linear-gradient(135deg, #D4AF37 0%, #B8960C 100%) !important;
    color: #080C14 !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 12px 24px !important;
    width: 100% !important;
    letter-spacing: 0.5px !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.88 !important; }

/* ── Dataframe ── */
.stDataFrame { border-radius: 10px; overflow: hidden; }

/* ── Input ── */
.stTextInput > div > div > input {
    background: #0D1420 !important;
    border: 1px solid #1E2840 !important;
    color: #E8EAF0 !important;
    border-radius: 8px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 13px !important;
}
.stToggle { accent-color: #D4AF37; }

/* ── Status messages ── */
.status-ok  { background:#052E16; border:1px solid #166534; border-radius:8px; padding:10px 14px; color:#4ADE80; font-size:13px; margin:6px 0; }
.status-err { background:#2D0A0A; border:1px solid #991B1B; border-radius:8px; padding:10px 14px; color:#F87171; font-size:13px; margin:6px 0; }
.status-esc { background:#1F0A3C; border:1px solid #6B21A8; border-radius:8px; padding:10px 14px; color:#C084FC; font-size:13px; margin:6px 0; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        💳 TCI Finance Agent
        <span>AI Enablement Internship · Task 2</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**⚙️ Controls**")
    csv_path = st.text_input("CSV Path", value="invoices.csv")
    dry_run  = st.toggle("Dry Run Mode", value=True)

    if dry_run:
        st.markdown('<div class="status-ok">✅ Dry run ON — no real emails sent</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-err">⚠️ LIVE mode — emails will be sent</div>', unsafe_allow_html=True)

    st.markdown("---")
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        st.markdown('<div class="status-ok">🤖 Gemini API connected</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-err">⚡ Demo mode (no API key)</div>', unsafe_allow_html=True)

    st.markdown("---")
    run_btn = st.button("🚀 Run Agent Now")

    st.markdown("---")
    st.markdown("""
    <div style="font-size:11px; color:#4B5A7A; line-height:1.8;">
    <b style="color:#6B7A9A">Stage Matrix</b><br>
    🟢 Stage 1 · 1–7 days<br>
    🔵 Stage 2 · 8–14 days<br>
    🟡 Stage 3 · 15–21 days<br>
    🔴 Stage 4 · 22–30 days<br>
    🟣 Stage 5 · 30+ → Legal
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  HERO
# ══════════════════════════════════════════════

st.markdown("""
<div class="hero">
    <div class="hero-tag">Travel Corporation India Ltd · Finance Operations</div>
    <h1 class="hero-title">Credit Follow-Up <span>Email Agent</span></h1>
    <p class="hero-sub">AI-powered payment recovery · Tone-aware escalation · Full audit trail</p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  LOAD DATA & METRICS
# ══════════════════════════════════════════════

STAGE_COLORS = {1:"green", 2:"blue", 3:"gold", 4:"red", 5:"red"}
STAGE_LABELS = {1:"Warm", 2:"Firm", 3:"Formal", 4:"Urgent", 5:"Legal"}

if os.path.exists(csv_path):
    df = pd.read_csv(csv_path)
    df["Stage"]  = df["days_overdue"].apply(lambda d: get_stage(int(d))["stage"])
    df["Tone"]   = df["days_overdue"].apply(lambda d: get_stage(int(d))["tone"])
    df["Amount"] = df["amount"].apply(lambda a: f"₹{int(a):,}")

    total_overdue = df["amount"].sum()
    to_email      = len(df[df["Stage"] < 5])
    to_escalate   = len(df[df["Stage"] == 5])

    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card gold">
            <div class="metric-label">Total Invoices</div>
            <div class="metric-value">{len(df)}</div>
            <div class="metric-sub">loaded from CSV</div>
        </div>
        <div class="metric-card blue">
            <div class="metric-label">Emails to Send</div>
            <div class="metric-value">{to_email}</div>
            <div class="metric-sub">stages 1–4</div>
        </div>
        <div class="metric-card red">
            <div class="metric-label">Escalations</div>
            <div class="metric-value">{to_escalate}</div>
            <div class="metric-sub">30+ days overdue</div>
        </div>
        <div class="metric-card green">
            <div class="metric-label">Total Overdue</div>
            <div class="metric-value">₹{total_overdue/100000:.1f}L</div>
            <div class="metric-sub">across all invoices</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Invoice Queue Table
    st.markdown("""
    <div class="section-header">
        <h2>📂 Invoice Queue</h2>
        <span class="section-badge">Live Data</span>
    </div>
    """, unsafe_allow_html=True)

    display_df = df[["invoice_no","client_name","Amount","due_date","days_overdue","Stage","Tone"]].copy()
    display_df.columns = ["Invoice", "Client", "Amount Due", "Due Date", "Days Overdue", "Stage", "Tone"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

else:
    st.markdown(f'<div class="status-err">❌ CSV not found at: <code>{csv_path}</code> — update the path in the sidebar</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  RUN AGENT
# ══════════════════════════════════════════════

if run_btn:
    if not os.path.exists(csv_path):
        st.error(f"CSV not found: {csv_path}")
    else:
        with st.spinner("🤖 Agent running — generating emails..."):
            try:
                results = run_agent(csv_path=csv_path)

                sent_count = sum(1 for r in results if r.get("action") == "DRY_RUN")
                esc_count  = sum(1 for r in results if r.get("action") == "ESCALATED")

                st.markdown(f'<div class="status-ok">✅ Agent complete — {sent_count} emails generated · {esc_count} escalated</div>', unsafe_allow_html=True)

                st.markdown("""
                <div class="section-header">
                    <h2>📧 Generated Emails</h2>
                    <span class="section-badge">This Run</span>
                </div>
                """, unsafe_allow_html=True)

                for r in results:
                    stage = r.get("stage", 5)
                    if r.get("action") == "ESCALATED":
                        st.markdown(f"""
                        <div class="escalation-card">
                            <div class="escalation-label">🚨 ESCALATED TO LEGAL REVIEW</div>
                            <div style="color:#E8EAF0; font-size:14px; font-weight:600;">{r['invoice_no']} · {r['client']}</div>
                            <div style="color:#6B7A9A; font-size:12px; margin-top:4px;">{r['days_overdue']} days overdue · No auto-email sent · Assigned to Finance Manager</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        stage_cls = f"stage-{stage}"
                        st.markdown(f"""
                        <div class="email-card">
                            <div class="email-invoice">{r['invoice_no']} · ₹{int(r['amount']):,} · {r['days_overdue']} days overdue
                                <span class="stage-pill {stage_cls}" style="margin-left:8px;">Stage {stage} · {r['tone']}</span>
                            </div>
                            <div class="email-subject">📨 {r.get('subject','')}</div>
                            <div class="email-body">{r.get('body','')}</div>
                        </div>
                        """, unsafe_allow_html=True)

            except Exception as e:
                st.markdown(f'<div class="status-err">❌ Error: {e}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  AUDIT TRAIL
# ══════════════════════════════════════════════

st.markdown("""
<div class="section-header">
    <h2>🗃️ Audit Trail</h2>
    <span class="section-badge">SQLite · PII Masked</span>
</div>
""", unsafe_allow_html=True)

if os.path.exists("logs/audit.db"):
    conn     = sqlite3.connect("logs/audit.db")
    audit_df = pd.read_sql("SELECT * FROM email_log ORDER BY id DESC LIMIT 50", conn)
    conn.close()

    sent_a = len(audit_df[audit_df["is_escalation"] == 0])
    esc_a  = len(audit_df[audit_df["is_escalation"] == 1])

    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card gold">
            <div class="metric-label">Total Logged</div>
            <div class="metric-value">{len(audit_df)}</div>
        </div>
        <div class="metric-card blue">
            <div class="metric-label">Emails Sent</div>
            <div class="metric-value">{sent_a}</div>
        </div>
        <div class="metric-card red">
            <div class="metric-label">Escalations</div>
            <div class="metric-value">{esc_a}</div>
        </div>
        <div class="metric-card green">
            <div class="metric-label">PII Status</div>
            <div class="metric-value" style="font-size:18px; padding-top:6px;">Masked ✓</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    show_cols = ["timestamp","invoice_no","client_name","client_email","stage","tone","send_status"]
    st.dataframe(audit_df[show_cols], use_container_width=True, hide_index=True)
else:
    st.markdown('<div class="status-err">No audit log yet — click Run Agent first</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  FOOTER
# ══════════════════════════════════════════════

st.markdown("""
<div style="margin-top:48px; padding-top:20px; border-top:1px solid #1E2840; text-align:center;">
    <span style="font-family:'DM Mono',monospace; font-size:11px; color:#2E3A55; letter-spacing:1px;">
        TRAVEL CORPORATION INDIA LTD · AI ENABLEMENT INTERNSHIP · TASK 2 · GEMINI 2.0 FLASH · PYDANTIC · SQLITE · STREAMLIT
    </span>
</div>
""", unsafe_allow_html=True)
