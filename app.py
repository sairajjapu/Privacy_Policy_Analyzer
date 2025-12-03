from flask import Flask, render_template, request, redirect, url_for, flash
import re, os, html, requests,smtplib, time
from werkzeug.utils import secure_filename
from pathlib import Path
from PyPDF2 import PdfReader
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
from deep_translator import GoogleTranslator
from docx import Document


# ---------------- Flask App ----------------
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_secret_key")

# ---------------- Upload Config ----------------
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
MAX_FILE_SIZE = 5 * 1024 * 1024   # 5 MB
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# ---------------- Allowed Patterns ----------------
VALID_PATTERNS = [
      # Privacy policies
    r"privacy",                       # Privacy                          
    r"terms"                          # Terms
    r"privacy[-_\s]?policy",          # Privacy Policy
    r"privacypolicy",          # PrivacyPolicy
    r"privacy[-_\s]?statement",       # Privacy Statement
    r"privacy[-_\s]?notice",          # Privacy Notice
    r"privacy[-_\s]?agreement",       # Privacy Agreement
    r"data[-_\s]?protection",         # Data Protection

    # Terms of service / terms & conditions
    r"terms[-_\s]?of[-_\s]?service",  # Terms of Service
    r"terms[-_\s]?and[-_\s]?conditions",  # Terms and Conditions
    r"user[-_\s]?agreement",          # User Agreement
    r"acceptable[-_\s]?use",          # Acceptable Use Policy
    r"end[-_\s]?user[-_\s]?license",  # End User License Agreement (EULA)

    # Cookie policies
    r"cookie[-_\s]?policy",           # Cookie Policy
    r"cookie[-_\s]?notice",           # Cookie Notice
    r"cookie[-_\s]?statement",        # Cookie Statement
    r"use[-_\s]?of[-_\s]?cookies",    # Use of Cookies

    # General legal documents
    r"legal[-_\s]?notice",            # Legal Notice
    r"legal[-_\s]?disclaimer",        # Legal Disclaimer
    r"legal[-_\s]?terms",             # Legal Terms
    r"disclaimer",                    # General Disclaimer
    r"consent[-_\s]?form",            # Consent Form
]

# ---------------- Load Keyword Patterns ----------------
with open("patterns.json", "r") as f:
    CATEGORY_DESCRIPTIONS = json.load(f)

# ---------------- Routes ----------------
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/analyze')
def analyze():
    return render_template('analyze.html')

@app.route('/team')
def team():
    return render_template('team.html')

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/submit_contact", methods=["POST"])
def submit_contact():
    name = html.escape(request.form.get("name")) # type: ignore
    email = html.escape(request.form.get("email")) # type: ignore
    subject = html.escape(request.form.get("subject")) # type: ignore
    message = html.escape(request.form.get("message")) # type: ignore

    if not name or not email or not message:
        flash("All fields are required.", "error")
        return redirect(url_for("contact"))

    success = send_contact_email(name, email, subject, message)
    flash("✅ Your message has been sent successfully!" if success else "❌ Failed to send your message.", "info")
    return redirect(url_for("contact"))

# ---- Analyze Result ----
# ---- Analyze Result ----
@app.route('/analyze_result', methods=['POST'])
def analyze_result():
    url = html.escape(request.form.get('url', ''))
    file = request.files.get('file')
    translate_lang = request.form.get('translate')  # "en", "hi", "te", or None

    text = None
    # ---- Case 1: URL ----
    if url:
        if not is_valid_policy_url(url):
            flash("Only Privacy Policy or Terms & Conditions links are allowed.", "error")
            return redirect(url_for('analyze'))

        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                text = response.text
            else:
                flash("Could not fetch the URL content.", "error")
                return redirect(url_for('analyze'))
        except Exception as e:
            print("Error fetching URL:", e)
            flash("Could not connect to the website.", "error")
            return redirect(url_for('analyze'))

    # ---- Case 2: PDF ----
    elif file and allowed_file(file.filename):  # type: ignore
        filename = secure_filename(file.filename)  # type: ignore
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > MAX_FILE_SIZE:
            flash("Document is too large (max 5MB).", "error")
            return redirect(url_for('analyze'))

        file.save(filepath)
        ext = filename.rsplit(".", 1)[1].lower()
        if ext == "pdf":
            text = extract_pdf_text(filepath)
        elif ext == "docx":
            text = extract_docx_text(filepath)
        elif ext == "txt":
            text = extract_txt_text(filepath)

        os.remove(filepath)

        if not text or not is_valid_policy_text(text):
            flash("Uploaded document is not a valid Privacy Policy or Terms & Conditions.", "error")
            return redirect(url_for('analyze'))
    else:
        flash("Please provide a valid PDF, DOCX, or TXT document", "error") 
        return redirect(url_for('analyze'))

    # ---- Step 2: Keyword Analysis on original text ----
    data = keyword_analysis(text)

    # ---- Step 3: Optional Translation ----
    translated_text = None
    if translate_lang in ["en", "hi", "te"]:
        translated_text = translate_text(text, translate_lang)

    # ---- Render result ----
    return render_template(
        'result.html',
        url=url if url else "Uploaded Document",
        critical=data["critical"],
        dark_flag=data["dark_flag"],
        translated_text=translated_text  # optional display
    )

# ---------------- Helpers ----------------
def is_valid_policy_url(url: str) -> bool:
    if not url.startswith("http"):
        return False
    return any(re.search(pattern, url.lower(),re.IGNORECASE) for pattern in VALID_PATTERNS)

def allowed_file(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else None
    print("Filename:", filename, "| Extension:", ext, "| Allowed:", ALLOWED_EXTENSIONS)
    return ext in ALLOWED_EXTENSIONS if ext else False

def extract_pdf_text(filepath: str) -> str:
    text = ""
    try:
        reader = PdfReader(filepath)
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception as e:
        print("PDF extraction error:", e)
    return text

def extract_docx_text(filepath: str) -> str:
    text = ""
    try:
        doc = Document(filepath)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        print("DOCX extraction error:", e)
    return text

def extract_txt_text(filepath: str) -> str:
    text = ""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception as e:
        print("TXT extraction error:", e)
    return text

def is_valid_policy_text(text: str) -> bool:
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in VALID_PATTERNS)

# ---------------- Keyword Analysis ----------------
def keyword_analysis(text: str) -> dict:
    """
    Check text against keywords from patterns.json.
    Returns categories with matches + descriptions.
    """
    text_lower = text.lower()
    found = {}

    for category, data in CATEGORY_DESCRIPTIONS.items():
        keywords = data.get("keywords", [])
        description = data.get("description", "")

        matches = [kw for kw in keywords if kw.lower() in text_lower]
        if matches:
            found[category] = {
                "description": description,
                "matches": matches
            }

    return {
        "critical": found,
        "harmless": {},  # extend if needed
        "dark_flag": len(found) > 0
    }

# ---------------- Translation Helper ----------------
def translate_text(text: str, target_language: str) -> str:
    supported = {"en": "english", "hi": "hindi", "te": "telugu"}
    if target_language not in supported:
        return text
    try:
        return GoogleTranslator(source="auto", target=supported[target_language]).translate(text)
    except Exception as e:
        print("Translation error:", e)
        return text

# ---------------- Hybrid Analysis ----------------
def hybrid_analysis(text: str, target_language: str = None) -> dict: # type: ignore
    if target_language in ["en", "hi", "te"]:
        text = translate_text(text, target_language)
    return keyword_analysis(text)

def send_contact_email(name, email, subject, message):
    subject_line = f"New Contact Message from {name}"
    html_content = f"""
    <h2>Privacy Policy Analyzer</h2>
    <p><b>Name:</b> {name}</p>
    <p><b>Email:</b> {email}</p>
    <p><b>Subject:</b> {subject}</p>
    <p><b>Message:</b><br>{message}</p>
    """
    smtp_user=os.getenv("SMTP_USER")
    smtp_password=os.getenv("SMTP_PASSWORD")
    smtp_server=os.getenv("SMTP_SERVER")
    smtp_admin=os.getenv("SMTP_ADMIN")
    smtp_port=int(os.getenv("SMTP_PORT", 587))

    msg = MIMEMultipart()
    msg["From"] = smtp_user # type: ignore
    msg["To"] = smtp_admin # type: ignore
    msg["Subject"] = subject_line
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server: # type: ignore
            server.starttls()
            server.login(smtp_user, smtp_password) # type: ignore
            server.sendmail(smtp_user, smtp_admin, msg.as_string()) # type: ignore
        return True
    except Exception as e:
        print("Error sending email:", e)
        return False

# ---------------- Run App ----------------
if __name__ == '__main__':
    app.run(debug=True)
