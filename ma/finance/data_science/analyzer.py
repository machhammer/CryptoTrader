import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import pandas as pd

nltk.download("all")
analyzer = SentimentIntensityAnalyzer()


def preprocess_text(text):
    # Tokenize the text
    tokens = word_tokenize(text.lower())

    # Remove stop words
    filtered_tokens = [
        token for token in tokens if token not in stopwords.words("english")
    ]

    # Lemmatize the tokens
    lemmatizer = WordNetLemmatizer()
    lemmatized_tokens = [lemmatizer.lemmatize(token) for token in filtered_tokens]

    # Join the tokens back into a string
    processed_text = " ".join(lemmatized_tokens)

    return processed_text


def get_sentiment(text):
    scores = analyzer.polarity_scores(text)

    # sentiment = 1 if scores["pos"] > 0 else 0
    sentiment = scores["pos"]
    return sentiment


def sentiment_analysis(list_of_dicts):
    dataset = pd.DataFrame(list_of_dicts)
    dataset["summary"] = dataset["summary"].apply(preprocess_text)
    dataset["sentiment"] = dataset["summary"].apply(get_sentiment)
    return dataset.to_dict(orient="records")
