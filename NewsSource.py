import csv
import requests
import credentials

from abc import ABC, abstractmethod



class NewsSource(ABC):

    def __init__(self, name, key, url):
        self.name = name
        self.key = key
        self.url = url


    @abstractmethod
    def name(self):
        pass

    @abstractmethod
    def load(self):
        pass



class CoinDesk(NewsSource):

    def name(self):
        return self.name

    def load(self):
        response = requests.get(self.url,
                params={"lang":"EN","limit":"100","api_key":self.key},
                headers={"Content-type":"application/json; charset=UTF-8"}
            ).json()
        return self.__format(response)

    def __format(self, articles):
        articles = articles.get("Data", [])
        formatted_articles = "\n\n".join(
            [f"Title: {article['TITLE']}\nDescription: {article['BODY']}"
            for article in articles]
        )
        return formatted_articles


class NewsApi(NewsSource):

    def name(self):
        return self.name

    def load(self):
        response = requests.get(self.url + self.key).json()
        return self.__format(response)

    def __format(self, articles):
        articles = articles.get('articles', [])
        formatted_articles = "\n\n".join(
            [f"Title: {article['title']}\nDescription: {article['description']}"
            for article in articles]
        )
        return formatted_articles
    

class MarketAux(NewsSource):

    def name(self):
        return self.name

    def load(self):
        response = requests.get(self.url + self.key).json()
        return self.__format(response)

    def __format(self, articles):
        articles = articles.get('articles', [])
        formatted_articles = "\n\n".join(
            [f"Title: {article['title']}\nDescription: {article['description']}"
            for article in articles]
        )
        return formatted_articles


class Cryptopanic(NewsSource):

    def name(self):
        return self.name

    def load(self):
        response = requests.get(self.url,
                params={
                   "auth_token": "baa901ccc69f264d33369c021ac1012205eefb62",  # replace with your key
                    "filter": "hot",               # hot | rising | bullish | bearish | important | lol
                    "public": "true"               # public news only
                }
        ).json()
        print(response)
        return self.__format(response)

    def __format(self, articles):
        articles = articles.get('articles', [])
        formatted_articles = "\n\n".join(
            [f"Title: {article['title']}\nDescription: {article['description']}"
            for article in articles]
        )
        return formatted_articles


def fetch_news():
    for news_source in credentials.news_sources:
        print(news_source['class'])
        source_instances = globals()[news_source['class']](news_source['class'], news_source['key'], news_source['url'])
        articles = "\n\n" + source_instances.load()
        print(articles)
    articles = articles.replace('"', '')
    return articles

def save_news(articles):
    with open('articles.csv', 'w', encoding='utf-8') as f:
        f.write(articles)

def load_news():
    with open('articles.csv', 'r', encoding='utf-8') as f:
        data = f.read()
    return data


