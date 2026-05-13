"""
================================================
Finance Credit Follow-Up Email Agent
Task 2 — AI Enablement Internship
Company: Travel Corporation India Ltd
Author: Deveshi Nautiyal
LLM: Google Gemini 2.0 Flash (Free Tier)
Framework: Custom ReAct Pipeline + Pydantic v2
================================================
"""

import os, json, re, sqlite3, time
import pandas as pd
import urllib.request, urllib.error
from datetime import datetime
from pydantic import BaseModel, field_validator
from typing import Literal, Optional
from dotenv import load_dotenv

load_dotenv()

# ══════════════════════════════════════════════
#  PYDANTIC MODELS  (Hallucination Guard)
# ══════════════════════════════════════════════

class EmailOutput(BaseModel):
    subject: str
    body: str
    stage: int
    tone: str
    invoice_no: str
    client_name: str
    amount: float
    days_overdue: int

    @field_validator("subject", "body")
    @classmethod
    def no_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Field must not be empty — possible hallucination")
        return v.strip()

class EscalationFlag(BaseModel):
    invoice_no: str
    client_name: str
    amount: float
    days_overdue: int
    action: Literal["ESCALATE_TO_LEGAL"]
    reason: str

# ══════════════════════════════════════════════
#  TONE ESCALATION ENGINE
# ══════════════════════════════════════════════

def get_stage(days: int) -> dict:
    """Map days overdue → escalation stage and tone."""
    if days <= 7:    return {"stage": 1, "tone": "Warm & Friendly",   "label": "1st Follow-Up"}
    elif days <= 14: return {"stage": 2, "tone": "Polite but Firm",   "label": "2nd Follow-Up"}
    elif days <= 21: return {"stage": 3, "tone": "Formal & Serious",  "label": "3rd Follow-Up"}
    elif days <= 30: return {"stage": 4, "tone": "Stern & Urgent",    "label": "4th Follow-Up"}
    else:            return {"stage": 5, "tone": "ESCALATE",          "label": "Legal Escalation"}

# ══════════════════════════════════════════════
#  PROMPT DESIGN
# ══════════════════════════════════════════════

SYSTEM_PROMPT = """You are a professional finance communication agent for Travel Corporation India Ltd.
Your sole task: generate personalised payment follow-up emails for overdue invoices.

HARD RULES (violations = rejected output):
1. Reply ONLY with valid JSON: {"subject": "...", "body": "..."}
2. NEVER output markdown, preamble, or any text outside the JSON object.
3. Every email MUST include ALL of: client name, invoice number, exact amount (Rs.),
   due date, exact days overdue, payment link. Missing any = hallucination.
4. DO NOT invent any data. Use ONLY what is provided.
5. Match tone EXACTLY for the given stage.

TONE GUIDE:
- Stage 1 (Warm & Friendly): Casual greeting, assume honest oversight, positive CTA.
- Stage 2 (Polite but Firm): Request explicit payment date confirmation.
- Stage 3 (Formal & Serious): Formal language, mention credit impact, 48hr deadline.
- Stage 4 (Stern & Urgent): Final notice, explicit legal escalation warning, 24hr deadline.
"""

def build_prompt(row: dict, stage_info: dict) -> str:
    return f"""Generate a Stage {stage_info['stage']} ({stage_info['tone']}) follow-up email.

DATA (use all fields exactly as given):
CLIENT NAME    : {row['client_name']}
INVOICE NUMBER : {row['invoice_no']}
AMOUNT DUE     : Rs.{int(row['amount']):,}
ORIGINAL DUE   : {row['due_date']}
DAYS OVERDUE   : {row['days_overdue']}
PAYMENT LINK   : {row['payment_link']}
CONTACT PHONE  : {row['contact_phone']}
PREV REMINDERS : {row['follow_up_count']}

Respond ONLY with: {{"subject": "...", "body": "..."}}"""

# ══════════════════════════════════════════════
#  GEMINI API CALL (with retry logic)
# ══════════════════════════════════════════════

def call_gemini(api_key: str, user_prompt: str, max_retries: int = 3) -> str:
    """Call Gemini 2.0 Flash with exponential backoff on rate limits."""
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={api_key}"
    )
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents":           [{"parts": [{"text": user_prompt}]}],
        "generationConfig":   {"temperature": 0.2, "maxOutputTokens": 800}
    }
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )

    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            return result["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 30 * (attempt + 1)
                print(f"    Rate limited → waiting {wait}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
            else:
                raise
    raise Exception(f"Gemini API failed after {max_retries} retries (429 rate limit)")

# ══════════════════════════════════════════════
#  DEMO MODE (no API needed)
# ══════════════════════════════════════════════

DEMO_EMAILS = {
    1: {
        "subject": "Quick Reminder – Invoice #{inv} | Rs.{amt} Due",
        "body": (
            "Hi {first},\n\nI hope you're doing well! "
            "This is a friendly reminder that Invoice #{inv} for Rs.{amt} "
            "was due on {due}, now {days} days ago.\n\n"
            "If you've already processed this, please disregard. "
            "Otherwise, you can pay quickly here:\n"
            "👉 {link}\n\n"
            "Questions? Call us: {phone}\n\n"
            "Thank you and we look forward to your continued partnership!\n\n"
            "Warm regards,\nFinance Team\nTravel Corporation India Ltd"
        )
    },
    2: {
        "subject": "Payment Pending – Invoice #{inv} ({days} Days Overdue)",
        "body": (
            "Dear {name},\n\n"
            "We hope this finds you well. Invoice #{inv} for Rs.{amt}, "
            "due on {due}, remains unpaid — now {days} days overdue.\n\n"
            "Could you please confirm your payment date or process it here:\n"
            "👉 {link}\n\n"
            "For any concerns, reach us at {phone}.\n\n"
            "Regards,\nFinance Team\nTravel Corporation India Ltd"
        )
    },
    3: {
        "subject": "IMPORTANT: Outstanding Payment – Invoice #{inv} ({days} Days Overdue)",
        "body": (
            "Dear {name},\n\n"
            "Despite our previous reminders, Invoice #{inv} for Rs.{amt} "
            "due on {due} remains unpaid — now {days} days overdue.\n\n"
            "Continued non-payment may impact your credit terms with us. "
            "We formally request your response within 48 hours:\n"
            "👉 {link}\n\nContact: {phone}\n\n"
            "Yours sincerely,\nFinance Department\nTravel Corporation India Ltd"
        )
    },
    4: {
        "subject": "FINAL NOTICE – Invoice #{inv} – Immediate Action Required",
        "body": (
            "Dear {name},\n\n"
            "This is our FINAL reminder. Invoice #{inv} for Rs.{amt} "
            "is now {days} days overdue. We have sent multiple reminders "
            "with no resolution.\n\n"
            "Failure to remit within 24 hours will result in escalation "
            "to our legal and recovery team.\n\n"
            "Pay Immediately: {link}\nOr call: {phone}\n\n"
            "Finance & Legal Department\nTravel Corporation India Ltd"
        )
    }
}

def generate_demo_email(row: dict, stage_info: dict) -> EmailOutput:
    """Generate email from templates — no API needed."""
    tmpl = DEMO_EMAILS[stage_info["stage"]]
    fmt  = dict(
        inv   = row["invoice_no"],
        amt   = f"{int(row['amount']):,}",
        due   = row["due_date"],
        days  = row["days_overdue"],
        link  = row["payment_link"],
        phone = row["contact_phone"],
        name  = row["client_name"],
        first = row["client_name"].split()[0],
    )
    return EmailOutput(
        subject      = tmpl["subject"].format(**fmt),
        body         = tmpl["body"].format(**fmt),
        stage        = stage_info["stage"],
        tone         = stage_info["tone"],
        invoice_no   = row["invoice_no"],
        client_name  = row["client_name"],
        amount       = float(row["amount"]),
        days_overdue = int(row["days_overdue"]),
    )

def generate_email(api_key: Optional[str], row: dict, stage_info: dict) -> EmailOutput:
    """Use Gemini if key available, else fall back to demo templates."""
    if api_key:
        try:
            raw = call_gemini(api_key, build_prompt(row, stage_info))
            raw = re.sub(r"^```json\s*", "", raw.strip())
            raw = re.sub(r"\s*```$",     "", raw)
            parsed = json.loads(raw)
            return EmailOutput(
                subject      = parsed["subject"],
                body         = parsed["body"],
                stage        = stage_info["stage"],
                tone         = stage_info["tone"],
                invoice_no   = row["invoice_no"],
                client_name  = row["client_name"],
                amount       = float(row["amount"]),
                days_overdue = int(row["days_overdue"]),
            )
        except Exception as e:
            print(f"    Gemini failed ({e}) → using demo template")
    return generate_demo_email(row, stage_info)

# ══════════════════════════════════════════════
#  AUDIT TRAIL (SQLite)
# ══════════════════════════════════════════════

def init_db() -> sqlite3.Connection:
    os.makedirs("logs", exist_ok=True)
    conn = sqlite3.connect("logs/audit.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS email_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp    TEXT,
            invoice_no   TEXT,
            client_name  TEXT,
            client_email TEXT,
            amount       REAL,
            days_overdue INTEGER,
            stage        INTEGER,
            tone         TEXT,
            subject      TEXT,
            body         TEXT,
            send_status  TEXT,
            is_escalation INTEGER DEFAULT 0
        )""")
    conn.commit()
    return conn

def _mask(email: str) -> str:
    """PII mitigation: mask email in logs."""
    parts = email.split("@")
    return parts[0][:3] + "***@" + parts[1]

def log_email(conn, record: dict, email: EmailOutput, status: str):
    conn.execute(
        "INSERT INTO email_log VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)",
        (datetime.now().isoformat(), email.invoice_no, email.client_name,
         _mask(record["client_email"]), email.amount, email.days_overdue,
         email.stage, email.tone, email.subject, email.body, status, 0)
    )
    conn.commit()

def log_escalation(conn, record: dict, flag: EscalationFlag):
    conn.execute(
        "INSERT INTO email_log VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)",
        (datetime.now().isoformat(), flag.invoice_no, flag.client_name,
         _mask(record["client_email"]), flag.amount, flag.days_overdue,
         5, "ESCALATE", "N/A – Escalated to Legal", flag.reason,
         "FLAGGED_FOR_LEGAL", 1)
    )
    conn.commit()

# ══════════════════════════════════════════════
#  DRY-RUN SEND
# ══════════════════════════════════════════════

def dry_run_send(to: str, email: EmailOutput):
    os.makedirs("logs", exist_ok=True)
    entry = {
        "timestamp":    datetime.now().isoformat(),
        "to":           to,
        "stage":        email.stage,
        "tone":         email.tone,
        "invoice_no":   email.invoice_no,
        "subject":      email.subject,
        "body_preview": email.body[:150] + "..."
    }
    with open("logs/dry_run_sends.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")

# ══════════════════════════════════════════════
#  MAIN AGENT LOOP
# ══════════════════════════════════════════════

def run_agent(csv_path: str = "invoices.csv") -> list:
    print("\n" + "═"*56)
    print("  Finance Credit Follow-Up Email Agent")
    print("  Travel Corporation India Ltd")
    print("  Powered by Google Gemini 2.0 Flash")
    print("═"*56)

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}\nMake sure invoices.csv is in the same folder as agent.py")

    df      = pd.read_csv(csv_path)
    api_key = os.getenv("GEMINI_API_KEY")

    if api_key:
        print(f"\n  ✅ GEMINI_API_KEY found — using live AI generation")
    else:
        print(f"\n  ⚡ No GEMINI_API_KEY — running in DEMO mode (template emails)")

    print(f"  📂 Loaded {len(df)} records from {csv_path}\n")

    conn    = init_db()
    results = []

    for _, row in df.iterrows():
        row        = row.to_dict()
        stage_info = get_stage(int(row["days_overdue"]))

        print(f"  [{row['invoice_no']}] {row['client_name']} — {row['days_overdue']} days overdue")

        # Stage 5 = Legal escalation, no email sent
        if stage_info["stage"] == 5:
            flag = EscalationFlag(
                invoice_no   = row["invoice_no"],
                client_name  = row["client_name"],
                amount       = float(row["amount"]),
                days_overdue = int(row["days_overdue"]),
                action       = "ESCALATE_TO_LEGAL",
                reason       = (
                    f"{row['invoice_no']} is {row['days_overdue']} days overdue. "
                    f"4+ reminders exhausted. Requires legal/finance manager review."
                )
            )
            log_escalation(conn, row, flag)
            print(f"  🚨 ESCALATED TO LEGAL — no email sent\n")
            results.append({
                "invoice_no":   row["invoice_no"],
                "client":       row["client_name"],
                "amount":       row["amount"],
                "days_overdue": row["days_overdue"],
                "action":       "ESCALATED",
                "stage":        5,
                "tone":         "Legal Review",
            })
            continue

        try:
            email = generate_email(api_key, row, stage_info)
            dry_run_send(row["client_email"], email)
            log_email(conn, row, email, "DRY_RUN_SUCCESS")

            print(f"  ✅ Stage {stage_info['stage']} ({stage_info['tone']})")
            print(f"     Subject: {email.subject}\n")

            results.append({
                "invoice_no":   row["invoice_no"],
                "client":       row["client_name"],
                "amount":       row["amount"],
                "days_overdue": row["days_overdue"],
                "action":       "DRY_RUN",
                "stage":        stage_info["stage"],
                "tone":         stage_info["tone"],
                "subject":      email.subject,
                "body":         email.body,
            })

        except Exception as e:
            print(f"  ❌ ERROR: {e}\n")

    os.makedirs("output", exist_ok=True)
    with open("output/email_run_report.json", "w") as f:
        json.dump(results, f, indent=2)

    conn.close()

    sent       = sum(1 for r in results if r["action"] == "DRY_RUN")
    escalated  = sum(1 for r in results if r["action"] == "ESCALATED")

    print("═"*56)
    print(f"  ✅ Done!  {sent} emails generated  |  {escalated} escalated")
    print(f"  📄 Report  → output/email_run_report.json")
    print(f"  🗃️  Audit   → logs/audit.db")
    print(f"  📬 Log     → logs/dry_run_sends.jsonl")
    print("═"*56 + "\n")

    return results


if __name__ == "__main__":
    run_agent()
