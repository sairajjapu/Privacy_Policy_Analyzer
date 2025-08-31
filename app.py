from flask import Flask, render_template, request, redirect, url_for, flash
import spacy
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- SMTP CONFIG ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "japukannayya@gmail.com"
SMTP_PASSWORD = "zeeo zvzl njry dzjq"   # App password, not your Gmail login


app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Required for flash messages

nlp_spacy = spacy.load("en_core_web_sm")

# Critical Phrases
critical_phrases = [
    "share your data", "third parties", "sell your data",
    "advertising partners", "additional charges", "fees may apply",
    "consent automatically", "subject to change", "without notification",
    "we are not responsible", "we reserve the right",
    "binding arbitration", "limit your rights", "mandatory consent", "hidden costs"
]

def fetch_policy_text(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')
        text = ' '.join([p.get_text() for p in paragraphs])
        return text
    except Exception as e:
        print(f"Error fetching page: {e}")
        return ""

def simplify_sentence(sentence):
    doc = nlp_spacy(sentence)
    simplified = [token.text for token in doc if token.dep_ in ('nsubj', 'dobj', 'ROOT', 'pobj', 'attr', 'nmod')]
    return ' '.join(simplified)

def is_critical(sentence_text):
    return any(phrase in sentence_text.lower() for phrase in critical_phrases)

def analyze_text_sentiment(text):
    blob = TextBlob(text)
    sentences = blob.sentences
    critical_sentences = []
    harmless_sentences = []
    dark_pattern_reported = False

    for sentence in sentences:
        sentence_text = sentence.raw.lower()
        if is_critical(sentence_text):
            simplified = simplify_sentence(sentence.raw)
            critical_sentences.append(simplified)
            dark_pattern_reported = True
        else:
            harmless_sentences.append(sentence.raw.strip())
    return critical_sentences, harmless_sentences, dark_pattern_reported

def analyze_policy_url(url):
    text = fetch_policy_text(url)
    if not text:
        return [], [], False
    return analyze_text_sentiment(text)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/analyze')
def analyze():
    return render_template('analyze.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

def send_contact_email(name, email,subject, message):
    subject = f"New Contact Message from {name}"
    
    html_content = f"""
    <h2>Privacy Policy Analyzer</h2>
    <h2>Contact Form Submission</h2>
    <p><b>Name:</b> {name}</p>
    <p><b>Email:</b> {email}</p>
    <p><b>Subject:</b> {subject}</p>
    <p><b>Message:</b><br>{message}</p>
    """
    SMTP_ADMIN="sairajjapu@gmail.com"
    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = SMTP_ADMIN   # send to yourself (admin email)
    msg["Subject"] = subject
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, SMTP_USER, msg.as_string())
        return True
    except Exception as e:
        print("Error sending email:", e)
        return False


@app.route('/submit_contact', methods=['POST'])
def submit_contact():
    name = request.form.get('name')
    email = request.form.get('email')
    subject = request.form.get('subject')
    message = request.form.get('message')

    if not name or not email or not message:
        flash("All fields are required.", "error")
        return redirect(url_for("contact"))

    # Send email via SMTP
    success = send_contact_email(name, email, subject, message)

    if success:
        flash("✅ Your message has been sent successfully!", "success")
    else:
        flash("❌ Failed to send your message. Please try again later.", "error")

    return redirect(url_for('contact'))




@app.route('/analyze_result', methods=['POST'])
def analyze_result():
    url = request.form.get('url')  # match form input name
    if not url:
        flash("Please provide a URL to analyze.", "error")
        return redirect(url_for('analyze'))

    language = request.form.get('language')
    critical, harmless, flag = analyze_policy_url(url)
    return render_template(
        'result.html',
        url=url,
        critical=critical,
        harmless=harmless,
        dark_flag=flag
    )


if __name__ == '__main__':
    app.run(debug=True)
