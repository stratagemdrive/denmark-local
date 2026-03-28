import feedparser
import json
import os
import requests
from datetime import datetime, timedelta, timezone
from googletrans import Translator
from dateutil import parser as date_parser

# Configuration
COUNTRY = "denmark"
RSS_FEEDS = {
    "DR": "https://www.dr.dk/nyheder/service/feeds/allenyheder",
    "Berlingske": "https://www.berlingske.dk/content/rss",
    "JydskeVestkysten": "https://jv.dk/feed/danmark",
    "Fyens Stiftstidende": "https://fyens.dk/feed/danmark",
    "The Local DK": "https://feeds.thelocal.com/rss/dk",
    "Nationalbanken": "https://www.nationalbanken.dk/en/rss-feeds"
}

CATEGORIES = ["Diplomacy", "Military", "Energy", "Economy", "Local Events"]
MAX_AGE_DAYS = 7
TARGET_PER_CAT = 20
FILE_PATH = f"docs/{COUNTRY}_news.json"

translator = Translator()

def get_category(text):
    text = text.lower()
    # Diplomacy
    if any(w in text for w in ['udenrigs', 'ambassadør', 'diplomati', 'eu', 'nato', 'fn', 'foreign affairs']): return "Diplomacy"
    # Military
    if any(w in text for w in ['forsvaret', 'militær', 'soldat', 'våben', 'fregat', 'ukraine', 'military']): return "Military"
    # Energy
    if any(w in text for w in ['energi', 'vindmøller', 'olie', 'gas', 'elpris', 'strøm', 'energy']): return "Energy"
    # Economy
    if any(w in text for w in ['økonomi', 'erhverv', 'aktier', 'inflation', 'rente', 'skat', 'economy']): return "Economy"
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

    # Use a real browser User-Agent to avoid 403 blocks
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    for source_name, url in RSS_FEEDS.items():
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            feed = feedparser.parse(resp.content)
            
            for entry in feed.entries:
                try:
                    pub_date = date_parser.parse(entry.published)
                    if pub_date.tzinfo is None:
                        pub_date = pub_date.replace(tzinfo=timezone.utc)
                    
                    if (now - pub_date).days > MAX_AGE_DAYS:
                        continue
                    
                    if entry.link not in seen_urls:
                        # Translate if necessary (The Local and Nationalbanken are already English)
                        if source_name in ["The Local DK", "Nationalbanken"]:
                            translated_title = entry.title
                        else:
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
                except Exception:
                    continue
        except Exception as e:
            print(f"Skipping {source_name} due to error: {e}")
            continue

    # Final cleanup and balancing
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
