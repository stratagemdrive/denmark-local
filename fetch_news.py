import feedparser
import json
import os
from datetime import datetime, timedelta, timezone
from googletrans import Translator
from dateutil import parser as date_parser

# Configuration
COUNTRY = "denmark"
RSS_FEEDS = {
    "DR": "https://www.dr.dk/nyheder/service/feeds/alle-nyheder",
    "Jyllands-Posten": "https://jyllands-posten.dk/?service=rssfeed&mode=latest",
    "TV2": "https://feeds.tv2.dk/nyheder/rss",
    "Fyens Stiftstidende": "https://fyens.dk/rss",
    "Arhus Stiftstidende": "https://stiften.dk/rss"
}

CATEGORIES = ["Diplomacy", "Military", "Energy", "Economy", "Local Events"]
MAX_AGE_DAYS = 7
TARGET_PER_CAT = 20
FILE_PATH = f"docs/{COUNTRY}_news.json"

translator = Translator()

def get_category(text):
    text = text.lower()
    if any(w in text for w in ['udenrigs', 'ambassadør', 'diplomati', 'eu', 'nato', 'fn']): return "Diplomacy"
    if any(w in text for w in ['forsvaret', 'militær', 'soldat', 'våben', 'fregat']): return "Military"
    if any(w in text for w in ['energi', 'vindmøller', 'olie', 'gas', 'grøn omstilling', 'elpris']): return "Energy"
    if any(w in text for w in ['økonomi', 'erhverv', 'aktier', 'inflation', 'rente', 'skat']): return "Economy"
    return "Local Events"

def fetch_and_process():
    if not os.path.exists("docs"):
        os.makedirs("docs")

    existing_data = []
    if os.path.exists(FILE_PATH):
        try:
            with open(FILE_PATH, 'r') as f:
                existing_data = json.load(f)
        except:
            existing_data = []

    new_stories = []
    seen_urls = {s['url'] for s in existing_data}
    now = datetime.now(timezone.utc)

    for source_name, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries:
            try:
                pub_date = date_parser.parse(entry.published)
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                
                if (now - pub_date).days > MAX_AGE_DAYS:
                    continue
                
                if entry.link not in seen_urls:
                    # Danish to English
                    translated_title = translator.translate(entry.title, src='da', dest='en').text
                    
                    story = {
                        "title": translated_title,
                        "source": source_name,
                        "url": entry.link,
                        "published_date": pub_date.strftime("%Y-%m-%d %H:%M:%S"),
                        "category": get_category(entry.title + " " + getattr(entry, 'summary', ''))
                    }
                    new_stories.append(story)
                    seen_urls.add(entry.link)
            except:
                continue

    all_stories = new_stories + existing_data
    fresh_stories = []
    seen = set()
    for s in all_stories:
        dt = datetime.strptime(s['published_date'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        if (now - dt).days <= MAX_AGE_DAYS and s['url'] not in seen:
            fresh_stories.append(s)
            seen.add(s['url'])

    fresh_stories.sort(key=lambda x: x['published_date'], reverse=True)

    final_output = []
    for cat in CATEGORIES:
        cat_group = [s for s in fresh_stories if s['category'] == cat][:TARGET_PER_CAT]
        final_output.extend(cat_group)

    with open(FILE_PATH, 'w') as f:
        json.dump(final_output, f, indent=4)

if __name__ == "__main__":
    fetch_and_process()
