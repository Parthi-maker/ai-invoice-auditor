import json
import sqlite3
import hashlib
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd
import streamlit as st

from invoice_processing import evaluate_invoice, extract_fields, read_upload

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "invoiceguard.db"

st.set_page_config(page_title="InvoiceGuard AI", page_icon="🛡️", layout="wide")

FIELDS = [
    "vendor", "invoice_number", "invoice_date", "due_date", "customer",
    "currency", "line_items", "subtotal", "tax_rate", "tax", "discount",
    "charges", "total", "amount_due", "amount_in_words",
]

def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uploaded_at TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            vendor TEXT,
            invoice_number TEXT,
            invoice_date TEXT,
            subtotal REAL,
            tax REAL,
            total REAL,
            currency TEXT,
            risk_score INTEGER,
            status TEXT,
            findings TEXT,
            extracted_text TEXT,
            extracted_data TEXT,
            score_adjustments TEXT,
            validation_results TEXT,
            confidence REAL
        )
        """)
        columns = {row[1] for row in con.execute("PRAGMA table_info(invoices)")}
        migrations = {
            "extracted_data": "TEXT",
            "score_adjustments": "TEXT",
            "validation_results": "TEXT",
            "confidence": "REAL",
        }
        for name, column_type in migrations.items():
            if name not in columns:
                con.execute(f"ALTER TABLE invoices ADD COLUMN {name} {column_type}")
        con.commit()

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()

def load_existing():
    with sqlite3.connect(DB_PATH) as con:
        return pd.read_sql_query("SELECT * FROM invoices ORDER BY id DESC", con)

def _json_default(value):
    if isinstance(value, Decimal):
        return float(value)
    return str(value)

def _csv_value(value):
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, default=_json_default)
    return _json_default(value)

def save_invoice(fields, file_hash, risk_score, status, findings, adjustments):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
        INSERT INTO invoices
        (uploaded_at,file_name,file_hash,vendor,invoice_number,invoice_date,subtotal,tax,total,currency,risk_score,status,findings,extracted_text,extracted_data,score_adjustments,validation_results,confidence)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            datetime.now().isoformat(timespec="seconds"), fields["file_name"], file_hash,
            fields["vendor"], fields["invoice_number"], fields["invoice_date"],
            float(fields["subtotal"]) if fields["subtotal"] is not None else None,
            float(fields["tax"]) if fields["tax"] is not None else None,
            float(fields["total"]) if fields["total"] is not None else None,
            fields["currency"],
            risk_score, status, json.dumps(findings), fields["extracted_text"],
            json.dumps(fields, default=_json_default), json.dumps(adjustments),
            json.dumps(fields["validation_results"], default=_json_default), fields["confidence"]
        ))
        con.commit()

def demo_text():
    return """ACME OFFICE SUPPLIES
Vendor: Acme Office Supplies
Invoice Number: AC-2026-014
Invoice Date: 2026-10-01
Currency: INR
Subtotal: 10000.00
GST (18%): 1800.00
Grand Total: 11800.00
"""

init_db()
st.title("🛡️ InvoiceGuard AI")
st.caption("Smart invoice verification, duplicate detection and anomaly review")
st.info("Prototype note: flagged records are risk indicators, not proof of fraud. Review original documents before taking action.")

with st.sidebar:
    st.header("Navigation")
    page = st.radio("Choose a page", ["Upload & Analyze", "Invoice History", "Evaluation & Notes"])
    st.divider()
    
if page == "Upload & Analyze":
    st.subheader("Upload an invoice")
    st.write("Supported: searchable/scanned PDF, JPG, PNG, TIFF, BMP, WEBP, TXT, and DOCX.")
    uploads = st.file_uploader(
        "Choose invoice files",
        type=["pdf", "png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp", "txt", "docx"],
        accept_multiple_files=True,
    )
    c1, c2 = st.columns([1, 2])
    with c1:
        use_demo = st.button("Load demo invoice text", use_container_width=True)
    if use_demo:
        class DemoUpload:
            name = "demo_invoice.txt"
            def getvalue(self):
                return demo_text().encode()
        uploads = [DemoUpload()]

    if uploads:
        existing = load_existing()
        for upload in uploads:
            text, data, method = read_upload(upload)
            st.markdown("---")
            st.write(f"**File:** {upload.name}  ·  **Reader:** {method}")
            if not text.strip():
                st.error(method.partition(":")[2].strip() or "Could not read text from this file.")
                continue
            fields = extract_fields(text, upload.name)
            digest = sha256_bytes(data)
            score, status, findings, adjustments = evaluate_invoice(
                fields, digest, existing.to_dict(orient="records")
            )
            with st.expander(f"Analysis: {upload.name}", expanded=True):
                left, right = st.columns([3, 2])
                with left:
                    st.markdown("**Extracted fields**")
                    display = {k: fields[k] for k in FIELDS}
                    st.json(json.loads(json.dumps(display, default=_json_default)))
                    st.markdown(f"**Extraction confidence (heuristic):** {fields['confidence']:.0%}")
                    st.markdown("**Calculation validation**")
                    for result in fields["validation_results"]:
                        if result["status"] == "pass":
                            st.success(result["message"])
                        elif result["status"] == "mismatch":
                            st.error(result["message"])
                        else:
                            st.warning(result["message"])
                with right:
                    critical_missing = not fields["vendor"] or fields["total"] is None
                    st.metric(
                        "Risk score (incomplete)" if critical_missing else "Risk score",
                        f"{score}/100",
                    )
                    if critical_missing:
                        st.warning("Critical fields are missing; do not rely on this score without manual review.")
                    else:
                        st.caption("Heuristic review signal, not a fraud probability.")
                    st.write(f"**Status:** {status}")
                    st.markdown("**Findings**")
                    for item in findings:
                        st.write("• " + item)
                    st.markdown("**Score adjustments**")
                    if adjustments:
                        for adjustment in adjustments:
                            st.write(f"• +{adjustment['points']} — {adjustment['reason']}")
                    else:
                        st.write("No score adjustments.")
                    if st.button("Save analysis to history", key=f"save_{upload.name}"):
                        save_invoice(fields, digest, score, status, findings, adjustments)
                        st.success("Saved to local history.")
                        existing = load_existing()
            with st.expander(f"Extracted document text (debugging): {upload.name}", expanded=False):
                st.text_area("OCR/text output", text, height=200, key=f"text_{upload.name}")
            result = {
                **{k: fields[k] for k in FIELDS},
                "confidence": fields["confidence"],
                "field_confidence": fields["field_confidence"],
                "validation_results": fields["validation_results"],
                "risk_score": score,
                "status": status,
                "findings": findings,
                "score_adjustments": adjustments,
            }
            st.download_button(
                "Download this result as JSON",
                data=json.dumps(result, indent=2, default=_json_default),
                file_name=f"{Path(upload.name).stem}_analysis.json",
                mime="application/json",
                key=f"json_{upload.name}"
            )
            csv_row = {
                key: _csv_value(value)
                for key, value in result.items()
            }
            st.download_button(
                "Download this result as CSV",
                data=pd.DataFrame([csv_row]).to_csv(index=False).encode("utf-8"),
                file_name=f"{Path(upload.name).stem}_analysis.csv",
                mime="text/csv",
                key=f"csv_{upload.name}",
            )
    else:
        st.markdown("#### Quick start")
        st.write("Use **Load demo invoice text** to test the workflow before uploading your own sample documents.")
        st.code(demo_text(), language="text")

elif page == "Invoice History":
    st.subheader("Saved invoice history")
    df = load_existing()
    if df.empty:
        st.info("No saved invoices yet. Analyze an invoice and click 'Save analysis to history'.")
    else:
        view_cols = ["id","uploaded_at","file_name","vendor","invoice_number","invoice_date","subtotal","tax","total","currency","risk_score","status"]
        st.dataframe(df[view_cols], use_container_width=True, hide_index=True)
        st.download_button("Export history as CSV", df[view_cols].to_csv(index=False).encode("utf-8"), "invoiceguard_history.csv", "text/csv")
        json_records = df.drop(columns=["extracted_text"], errors="ignore").to_dict(orient="records")
        st.download_button("Export history as JSON", json.dumps(json_records, indent=2, default=str), "invoiceguard_history.json", "application/json")
        st.markdown("**Findings by invoice**")
        for _, row in df.iterrows():
            with st.expander(f"#{row['id']} · {row['file_name']} · {row['status']}"):
                st.write(row["findings"])

else:
    st.subheader("Evaluation & research notes")
    st.markdown("""
    ### Recommended evaluation protocol
    1. Create a labeled test set containing normal invoices and controlled anomalies.
    2. Measure field extraction accuracy separately for vendor, invoice number, date, subtotal, tax and total.
    3. Measure duplicate-detection precision and recall.
    4. Measure anomaly precision, recall and false-positive rate.
    5. Compare rule-only detection with rule + Isolation Forest.
    6. Keep a held-out test set that is not used for tuning.

    ### Current prototype limitations
    - Invoice layouts vary; extracted fields and heuristic confidence should be checked against the original document.
    - OCR needs local Tesseract installation; scanned PDFs may also require Poppler.
    - Isolation Forest requires enough historical numeric examples and does not prove fraud.
    - Risk scores are heuristic review priorities, not calibrated fraud probabilities.
    - Tax rules vary by jurisdiction; only rates stated in the invoice are used by these checks.
    """)
    st.markdown("### Quick test checklist")
    st.checkbox("Normal invoice extracts the expected fields")
    st.checkbox("Same file uploaded twice triggers duplicate warning")
    st.checkbox("Changed total triggers arithmetic mismatch")
    st.checkbox("CSV and JSON exports open correctly")
    st.checkbox("Missing fields create a review warning")
