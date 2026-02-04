
import re, requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:\+44\s?\d{1,4}|0\d{2,4})\s?\d{3,4}\s?\d{3,4}")

def fetch(url: str) -> str:
    return requests.get(url, timeout=20, headers={"User-Agent":"SEN-College-Finder/1.0"}).text

def extract_contacts(html: str):
    emails = list(dict.fromkeys(EMAIL_RE.findall(html)))
    phones = list(dict.fromkeys(PHONE_RE.findall(html)))
    return emails, phones

def extract_open_day_candidates(html: str):
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(' ', strip=True)
    date_like = re.findall(r"(?:\d{1,2}\s+(?:Jan|January|Feb|February|Mar|March|Apr|April|May|Jun|June|Jul|July|Aug|August|Sep|Sept|September|Oct|October|Nov|November|Dec|December)\s+\d{4})", text)
    links = [a.get('href') for a in soup.find_all('a') if a.get('href')]
    return list(dict.fromkeys(date_like))[:10], list(dict.fromkeys(links))[:50]

def run_deep_dive(provider_id: str, links: dict):
    sources=[]; contacts_found=[]; open_days=[]
    for label, url in (links or {}).items():
        if not url: continue
        try:
            html = fetch(url)
            sources.append(url)
            emails, phones = extract_contacts(html)
            if emails or phones:
                contacts_found.append({"name": None, "role": label, "email": emails[0] if emails else None, "phone": phones[0] if phones else None, "source_url": url})
            dates, _ = extract_open_day_candidates(html)
            for d in dates[:2]:
                open_days.append({"date": None, "time": None, "type": "Open Event", "booking_url": url, "location": None, "notes": d, "source_url": url})
        except Exception:
            continue
    return {
        "provider_id": provider_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "contacts_found": contacts_found,
        "open_days": open_days,
        "send_offer_detail": {"summary": "(Generated summary of SEND/EHCP support)", "evidence": []},
        "course_offer_detail": {"summary": "(Generated summary of hospitality/catering offer)", "evidence": []},
        "questions_to_ask": [
            "How do you support reading/time management during practical sessions?",
            "What support ratio is available for EHCP learners?",
            "Do you offer quieter open events or pre-visit SEND meetings?"
        ],
        "sources_used": sources
    }
