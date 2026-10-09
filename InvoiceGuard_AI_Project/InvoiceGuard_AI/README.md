# InvoiceGuard AI — Smart Invoice Fraud Detection

A student-friendly AI/ML prototype for invoice extraction, arithmetic checks, duplicate detection, anomaly flags, review explanations, SQLite history, and CSV/JSON export.

> Safety/accuracy note: a risk flag is not proof of fraud. This project is a prototype and must not be used to automatically reject invoices or accuse suppliers.

## Features
- Streamlit dashboard
- Extract fields from PDFs, supported image files, TXT, and DOCX invoices
- OCR support for images through Tesseract
- Native PDF text extraction with PyMuPDF, with OCR fallback for scanned PDFs
- Label-aware invoice field extraction and arithmetic validation with decimal arithmetic
- Exact-file and field-based possible duplicate detection
- Isolation Forest anomaly signal when at least 10 historical numeric invoices exist
- SQLite history and CSV/JSON export
- Demo invoice for checking the workflow

## 1. Prerequisites
- Python 3.10 or newer
- Windows, macOS or Linux
- Internet access to install Python packages

For image OCR, install the **Tesseract OCR application** separately:
- Windows: install Tesseract OCR from a trusted Windows installer. Add its installation folder (commonly `C:\Program Files\Tesseract-OCR`) to `PATH`, or set `TESSERACT_CMD` to the full `tesseract.exe` path.
- macOS: `brew install tesseract`
- Ubuntu/Debian: `sudo apt install tesseract-ocr`

Scanned PDF OCR uses `pdf2image` and also requires Poppler:
- Windows: download a trusted Poppler for Windows build, extract it, and add its `Library\bin` or `bin` folder to `PATH`, or set `POPPLER_PATH` to that folder.
- macOS: `brew install poppler`
- Ubuntu/Debian: `sudo apt install poppler-utils`

Search official installation instructions for your operating system and use trusted package sources.
Restart the terminal after changing `PATH`, then check with `tesseract --version` and (for scanned PDFs) `pdftoppm -h`. In PowerShell, environment variables can be set for the current terminal with `$env:TESSERACT_CMD = 'C:\Program Files\Tesseract-OCR\tesseract.exe'` and `$env:POPPLER_PATH = 'C:\path\to\poppler\Library\bin'`.

## 2. Setup on Windows
Open Command Prompt or the VS Code terminal inside this project folder:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

The browser should open the local application. If it does not, visit the local URL printed by Streamlit, usually `http://localhost:8501`.

If `python` is not recognized, try `py` in place of `python`.

## 3. Test it
Run the regression suite from the project folder:

```bash
python -m unittest discover -s tests -v
```

1. Click **Load demo invoice text**.
2. Review the extracted fields, extraction confidence, calculation checks, and findings.
3. Click **Save analysis to history**.
4. Open **Invoice History**.
5. Export CSV or JSON.
6. Upload the same document twice to test duplicate detection.
7. Change `Grand Total` in a copied text invoice to test arithmetic mismatch.

## 4. Supported input
- Searchable PDF: text extracted using PyMuPDF first
- TXT: direct text parsing
- DOCX: paragraph and table text extraction using python-docx
- PNG/JPG/TIFF/BMP/WEBP: OCR using Tesseract
- Scanned PDF: OCR fallback using Tesseract, Poppler, and pdf2image

CSV is an export format in this MVP; invoice uploads are not parsed as arbitrary spreadsheet templates.

## 5. Current design and research work
This is a working baseline, not a production fraud detection service:
- Field extraction is label-aware and layout-dependent; verify extracted values against the source document.
- Duplicate detection uses file hash and a few normalized fields.
- Anomaly detection is optional and uses Isolation Forest on historical subtotal/tax/total data.
- Calculation checks use decimal arithmetic; unavailable or uncertain values are not substituted with zero.
- The risk score is a transparent heuristic review signal, not a probability of fraud.
- Human review is required for flagged cases.

For an academic evaluation, prepare a labeled dataset with normal and controlled altered invoices, hold out test examples, and report field-level accuracy, duplicate precision/recall, anomaly precision/recall, false-positive rate, and processing time. Do not claim model performance without running this evaluation.

## 6. Troubleshooting
- `ModuleNotFoundError`: activate `.venv`, then run `pip install -r requirements.txt`.
- OCR says unavailable: install Tesseract and ensure `tesseract.exe` is on PATH.
- Scanned PDF OCR fails: install Poppler and ensure its `bin` folder is on PATH.
- Fields are blank: inspect the extracted text and update extraction patterns for the invoice layout.
- Port is busy: run `streamlit run app.py --server.port 8502`.

## 7. Privacy
The app is designed to run locally and stores saved analyses in `invoiceguard.db` in the project folder. Use sample or appropriately authorized documents. Do not upload confidential invoices to services without permission.
