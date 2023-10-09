import feedparser
import config as cfg
from datetime import datetime
import dateutil.parser
import uuid
import re

feeds_url = cfg.news_feeds

CLEAN_HTML = re.compile("<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});")
CLEAN_ULR = re.compile(
    r"""(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))"""
)
CLEAN_IMG = re.compile("(<img.*?>)")


def clean_text(text):
    clean_text = re.sub(
        "(<img.*?>)", "", text, 0, re.IGNORECASE | re.DOTALL | re.MULTILINE
    )
    # clean_text = re.sub(CLEAN_ULR, "", clean_text)
    # clean_text = re.sub(CLEAN_HTML, "", clean_text)

    return clean_text


def to_dict(id, title, published, summary, url):
    # to_date = datetime.strptime(published, "%a, %d %b %Y %H:%M:%S %z")
    to_date = dateutil.parser.parse(published)
    return {
        "id": str(uuid.uuid4())[:8],
        "title": title.replace("'", ""),
        "published": to_date.strftime("%d/%m/%Y"),
        "summary": clean_text(summary),
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
            if not entry in results:
                results.append(
                    to_dict(entry.id, entry.title, entry.published, summary, url)
                )
    return results
