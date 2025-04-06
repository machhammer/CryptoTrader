import json
import requests
import credentials
from NewsSource import *
from openai import OpenAI

class SourceCode:
    COINDESK = 1
    NEWS_API = 2

client = OpenAI(
    api_key=credentials.openai.get("key")
)


def interpret_news_with_openai(news):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        store=True,
        messages=[
            {"role": "system", "content": "You are a financial analyst searching for opportunities"},
            {"role": "user", "content": f"What are the 5 coins which might face an increase in price today?:\n\n{news}"},
        ]
    )
    print("AI Summary:", completion.choices[0].message.content)


def main():
    print("Fetching cryptocurrency news from CoinDesk...")
    
    news = fetch_coindesk_news()

    if news:
        print("\nInterpreting news with OpenAI...\n")
        # Interpret the news using OpenAI API
        interpret_news_with_openai(news)
    else:
        print("No news data to analyze.")


if __name__ == "__main__":
    news = fetch_news()
    save_news(news)
    
    articles = load_news()
    interpret_news_with_openai(articles)



