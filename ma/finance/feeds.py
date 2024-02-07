import feedparser
import config

print(config.news_feeds)

feeds = config.news_feeds


for feed in feeds:
    
    print(feed)
    feed_entries = feedparser.parse(feed).entries
    print(len(feed_entries))

    for entry in feed_entries:

        article_title = entry.title
        article_link = entry.link
        article_published_at = entry.published # Unicode string
        article_published_at_parsed = entry.published_parsed # Time object
        # article_author = entry.author  DOES NOT EXIST
        content = entry.summary
        # article_tags = entry.tags  DOES NOT EXIST


        #print ("{}[{}]".format(article_title, article_link))
        #print ("Published at {}".format(article_published_at))
        # print ("Published by {}".format(article_author)) 
        print("Content {}".format(content))
        # print("catagory{}".format(article_tags))

if __name__ == "__main__":
    pass
