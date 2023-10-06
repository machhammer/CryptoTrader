from storage.NewsDB import CosmosDB


def news():
    db = CosmosDB()
    return db.query_news()
