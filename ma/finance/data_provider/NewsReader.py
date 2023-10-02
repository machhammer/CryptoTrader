import feedparser
import config as cfg
from datetime import datetime
import dateutil.parser
import uuid

feeds_url = cfg.news_feeds


def to_dict(id, title, published, summary, url):
    # to_date = datetime.strptime(published, "%a, %d %b %Y %H:%M:%S %z")
    to_date = dateutil.parser.parse(published)
    return {
        "id": str(uuid.uuid4())[:8],
        "title": title,
        "published": str(to_date),
        "summary": summary,
        "source": url,
        "sentiment": -1,
    }


def read_news_feeds():
    results = []
    for url in feeds_url:
        feed = feedparser.parse(url)
        print(url)
        for entry in feed.entries:
            summary = entry.summary if hasattr(entry, "summary") else entry.title
            results.append(
                to_dict(entry.id, entry.title, entry.published, summary, url)
            )
    return results
