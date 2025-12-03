from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer
import nltk

nltk.download('punkt')  # Only once needed

def ai_summarize(text, sentence_count=5):
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = TextRankSummarizer()
    summary = summarizer(parser.document, sentence_count)
    return " ".join(str(sentence) for sentence in summary)

def detect_dark_patterns(text):
    suspicious_keywords = [
        "share with third parties", "collect personal data", "track",
        "advertising", "sell", "opt-out", "third-party vendors", "cookies",
        "location data", "retain indefinitely", "your consent", "data brokers"
    ]
    lines = text.split('\n')
    flagged = [line.strip() for line in lines if any(keyword in line.lower() for keyword in suspicious_keywords)]
    return flagged
