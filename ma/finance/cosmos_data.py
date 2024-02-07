import data_provider.DataReader as data_provider
import data_provider.NewsReader as news_reader

# from data_science import analyzer
import datetime

from storage.NewsDB import CosmosDB
import json


mode = 2


db = CosmosDB()

if mode == 0:
    db.clean_db()

if mode == 1:
    db.create_db()

    feeds = news_reader.read_news_feeds()

    # feeds = analyzer.sentiment_analysis(feeds)

    db.store_news(feeds)


if mode == 2:
    news_feeds = db.query_news()

    for news in news_feeds:
        print(news)
