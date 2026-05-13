#  Finance Credit Follow-Up Email Agent


> An AI agent that automatically generates tone-escalating payment follow-up emails for overdue invoices — powered by **Google Gemini 2.0 Flash**, validated by **Pydantic**, logged in **SQLite**, and displayed on a **Streamlit** dashboard.

---

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [Agent Architecture](#agent-architecture)
3. [Features](#features)
4. [Setup Instructions](#setup-instructions)
5. [Technical Stack & Decision Log](#technical-stack--decision-log)
6. [Security Mitigations](#security-mitigations)
7. [Escalation Matrix](#escalation-matrix)
8. [Sample Output](#sample-output)
9. [Folder Structure](#folder-structure)

---

## Project Overview

Finance teams waste significant time manually chasing overdue payments. This agent automates the entire workflow:

- Reads overdue invoices from a CSV
- Determines the correct escalation stage per invoice (based on days overdue)
- Generates a personalised, tone-appropriate email via Gemini 2.0 Flash (falls back to templates if no API key)
- Dry-runs the send (logs to `.jsonl`) so no real emails are sent during testing
- Logs every action to a **SQLite audit database** with PII-masked client emails
- Displays everything on a dark, luxury-styled **Streamlit dashboard**

**Reduces DSO (Days Sales Outstanding)** while maintaining client relationships through professionally calibrated communication.

---

## Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AGENT ENTRY POINT                        │
│                   run_agent(csv_path)                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
          ┌────────────▼────────────┐
          │  1. DATA INGESTION      │
          │  pandas.read_csv()      │
          │  invoices.csv → df      │
          └────────────┬────────────┘
                       │  (for each row)
          ┌────────────▼────────────┐
          │  2. STAGE DETECTION     │
          │  get_stage(days_overdue)│
          │  → stage 1–5 + tone     │
          └────────────┬────────────┘
                       │
           ┌───────────┴───────────┐
           │                       │
    Stage 5 (Legal)         Stages 1–4 (Email)
           │                       │
  ┌────────▼────────┐    ┌─────────▼──────────┐
  │  EscalationFlag │    │  3. EMAIL GENERATION│
  │  Pydantic model │    │  Gemini 2.0 Flash   │
  │  No email sent  │    │  → EmailOutput model│
  └────────┬────────┘    └─────────┬──────────┘
           │                       │
           │             ┌─────────▼──────────┐
           │             │  4. DRY-RUN SEND    │
           │             │  logs/dry_run.jsonl │
           │             └─────────┬──────────┘
           │                       │
           └───────────┬───────────┘
                       │
          ┌────────────▼────────────┐
          │  5. AUDIT TRAIL         │
          │  SQLite: logs/audit.db  │
          │  PII-masked client email│
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │  6. REPORT OUTPUT       │
          │  output/email_run_      │
          │  report.json            │
          └─────────────────────────┘

  ┌───────────────────────────────────┐
  │  STREAMLIT DASHBOARD              │
  │  dashboard.py                     │
  │  • Metrics  • Invoice Queue       │
  │  • Email Preview  • Audit Table   │
  └───────────────────────────────────┘
```

---

## Features

| Feature | Implementation |
|---|---|
| Data Ingestion | `pandas.read_csv()` from `invoices.csv` |
| Tone Escalation Engine | `get_stage(days)` → 5-stage matrix |
| Email Generation | Gemini 2.0 Flash with fallback templates |
| Trigger Logic | Loops all rows, dispatches correct stage |
| Dry-Run Send | Appends to `logs/dry_run_sends.jsonl` |
| Audit Trail | SQLite `email_log` table with timestamps |
| Escalation Cap | Stage 5 → `EscalationFlag`, no email sent |
| Email Personalisation | All 6 required fields from CSV |
| Hallucination Guard | Pydantic `EmailOutput` + `EscalationFlag` models |
| PII Masking | Client emails masked in logs (`abc***@domain.com`) |
| Streamlit Dashboard | Metrics, queue, preview, audit trail |

---

## Setup Instructions

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd finance-email-agent
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up your API key
```bash
cp .env.example .env
# Edit .env and add your Gemini API key:
# GEMINI_API_KEY=your_key_here
```
> **No key?** The agent runs in demo mode using built-in email templates — no AI needed for testing.

### 5. Run the agent (CLI)
```bash
python agent.py
```

### 6. Launch the dashboard
```bash
streamlit run dashboard.py
```

---

## Technical Stack & Decision Log

### LLM: Google Gemini 2.0 Flash
| Attribute | Detail |
|---|---|
| **Model** | `gemini-2.0-flash` via Google Generative AI REST API |
| **Provider** | Google (free tier available) |
| **Why Gemini over GPT-4o / Claude** | Free-tier API access for internship/prototype use; 1M token context window; strong instruction-following for structured JSON output; no credit card required to start |
| **Temperature** | 0.2 — low, to reduce creative hallucination in financial emails |
| **Max Output Tokens** | 800 — sufficient for a professional email, prevents runaway generation |

### Agent Framework: Custom ReAct-style Pipeline
| Attribute | Detail |
|---|---|
| **Framework** | Custom pipeline (no LangChain/CrewAI) |
| **Architecture** | ReAct-inspired: Observe (CSV row) → Reason (get_stage) → Act (generate + send + log) |
| **Why not LangChain?** | Adds unnecessary abstraction for a linear workflow. A custom pipeline is easier to debug, has zero framework overhead, and makes audit logic explicit |
| **Why not CrewAI?** | Multi-agent orchestration is overkill for a single-purpose email agent with deterministic routing |

### Prompt Design

**System Prompt Philosophy:**
- Hard rules listed numerically so the LLM treats them as constraints, not suggestions
- Tone guide embedded in system prompt so stage context is always available
- Output format enforced as raw JSON `{"subject": "...", "body": "..."}` with explicit instruction to never use markdown or preamble
- Temperature 0.2 reinforces rule-following over creativity

**Key guardrails in prompt:**
```
HARD RULES (violations = rejected output):
1. Reply ONLY with valid JSON: {"subject": "...", "body": "..."}
2. NEVER output markdown, preamble, or any text outside the JSON object.
3. Every email MUST include ALL of: client name, invoice number, exact amount (Rs.),
   due date, exact days overdue, payment link. Missing any = hallucination.
4. DO NOT invent any data. Use ONLY what is provided.
```

**Prompt Iterations:**
- v1: Simple "write an email" prompt → LLM added fictional data (hallucination)
- v2: Added field list → LLM still wrapped output in markdown ```json blocks
- v3 (final): Added explicit "NEVER output markdown" rule + regex strip as backup

---

## Security Mitigations

| Risk | Description | Mitigation Applied |
|---|---|---|
| **Prompt Injection** | Malicious CSV data could manipulate LLM behaviour | Input data passed as structured key-value pairs in prompt, not raw concatenation. Pydantic validates output — any unexpected field fails loudly. |
| **Data Privacy / PII** | Client emails are personal data | Emails masked in all logs (`abc***@domain.com`) via `_mask()`. CSV data is never sent to the LLM in bulk — only per-row fields needed for that email. |
| **API Key Exposure** | Gemini API key could be leaked | Loaded via `python-dotenv` from `.env`. `.env` is in `.gitignore`. `.env.example` ships with placeholder values only. Never hardcoded anywhere in source. |
| **Hallucination Risk** | LLM generates invented client names, amounts, or dates | `EmailOutput` Pydantic model rejects empty fields. All financial fields (amount, days_overdue) are injected from CSV after generation, not trusted from LLM output. Temperature set to 0.2. |
| **Unauthorised Trigger** | Anyone could run the agent against production data | Dry-run mode is default (`ON`). No exposed HTTP endpoint — agent runs locally only. Dashboard requires local access. |
| **Email Spoofing** | Emails appearing from unverified sender | Dry-run mode prevents any real sending. For production: use SendGrid with verified sender domain + SPF/DKIM/DMARC configured on `tci.in` domain. |
| **Escalation Leak** | Stage 5 records might receive automated emails | `EscalationFlag` model enforces `action: "ESCALATE_TO_LEGAL"` via `Literal` type — agent hard-exits email generation for stage 5 before any API call. |

---

## Escalation Matrix

| Stage | Trigger | Tone | Key Message | CTA |
|---|---|---|---|---|
| Stage 1 | 1–7 days overdue | Warm & Friendly | Gentle reminder, assume oversight | Pay now link |
| Stage 2 | 8–14 days overdue | Polite but Firm | Payment still pending | Confirm payment date |
| Stage 3 | 15–21 days overdue | Formal & Serious | Escalating concern, credit impact | Respond within 48 hrs |
| Stage 4 | 22–30 days overdue | Stern & Urgent | Final reminder before escalation | Pay immediately or call |
| Stage 5 | 30+ days overdue | 🚨 Legal Flag | Human review required | Assign to finance manager |

---

## Sample Output

**Stage 1 — Warm & Friendly** (`INV-2025-001`, 5 days overdue)
```
Subject: Quick Reminder – Invoice #INV-2025-001 | Rs.45,000 Due

Hi Rajesh,

I hope you're doing well! This is a friendly reminder that Invoice #INV-2025-001
for Rs.45,000 was due on 2025-04-20, now 5 days ago.

If you've already processed this, please disregard. Otherwise, you can pay here:
https://pay.tci.in/INV-2025-001

Questions? Call us: +91-98765-43210

Thank you and we look forward to your continued partnership!

Warm regards,
Finance Team · Travel Corporation India Ltd
```

**Stage 5 — Legal Escalation** (`INV-2025-005`, 33 days overdue)
```
ESCALATED TO LEGAL REVIEW
INV-2025-005 · Vikram Singh · Rs.95,000
33 days overdue · No auto-email sent · Assigned to Finance Manager
```

---

## Folder Structure

```
finance-email-agent/
├── agent.py                  # Core agent logic
├── dashboard.py              # Streamlit dashboard
├── invoices.csv              # Sample invoice data
├── requirements.txt          # Python dependencies
├── .env.example              # API key template
├── .gitignore                # Excludes .env, __pycache__, outputs
├── README.md                 # This file
├── logs/
│   ├── audit.db              # SQLite audit trail (generated)
│   └── dry_run_sends.jsonl   # Dry-run email log (generated)
└── output/
    └── email_run_report.json # Full run report (generated)
```

---

*Built by Deveshi Nautiyal · Travel Corporation India Ltd · AI Enablement Internship*
