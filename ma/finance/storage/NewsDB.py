import azure.cosmos.documents as documents
import azure.cosmos.cosmos_client as cosmos_client
import azure.cosmos.errors as exceptions
import azure.cosmos.partition as PartitionKey
import datetime
import uuid
import credentials as config


HOST = config.cosmosdb["host"]
MASTER_KEY = config.cosmosdb["master_key"]
DATABASE_ID = config.cosmosdb["database_id"]
CONTAINER_ID = config.cosmosdb["container_id"]


class CosmosDB:
    def __init__(self):
        self.client = cosmos_client.CosmosClient(
            HOST,
            {"masterKey": MASTER_KEY},
            user_agent="ma",
            user_agent_overwrite=True,
        )

    def create_db(self):
        try:
            db = self.client.create_database(id=DATABASE_ID)
            print("Database with id '{0}' created".format(DATABASE_ID))

        except exceptions.CosmosResourceExistsError:
            db = self.client.get_database_client(DATABASE_ID)
            print("Database with id '{0}' was found".format(DATABASE_ID))

        # setup container for this sample
        try:
            self.container = db.create_container(
                id=CONTAINER_ID, partition_key=PartitionKey(path="/title")
            )
            print("Container with id '{0}' created".format(CONTAINER_ID))

        except exceptions.CosmosResourceExistsError:
            self.container = db.get_container_client(CONTAINER_ID)
            print("Container with id '{0}' was found".format(CONTAINER_ID))

    def clean_db(self):
        self.client.delete_database(DATABASE_ID)

    def query_news_by_attribute(self, attribute, value):
        query = (
            "SELECT i.title FROM Items i WHERE i." + attribute + " = '" + value + "'"
        )
        try:
            items = list(
                self.client.get_database_client(DATABASE_ID)
                .get_container_client(CONTAINER_ID)
                .query_items(
                    query=query,
                    enable_cross_partition_query=True,
                )
            )
        except Exception as error:
            print(error)
            print(query)

        return items

    def store_news(self, news):
        print("\nStoring News\n")
        i = 0
        e = 0
        d = 0
        for entry in news:
            i = i + 1
            try:
                if not self.query_news_by_attribute("title", entry["title"]):
                    self.container.create_item(body=entry)
                else:
                    d = d + 1
            except Exception as error:
                e = e + 1
                print(error)

        print("Number of news: " + str(i))
        print("Number or errors: " + str(e))
        print("Number or duplicates: " + str(d))

    def query_news(self):
        print("\nQuerying for Items\n")
        items = list(
            self.client.get_database_client(DATABASE_ID)
            .get_container_client(CONTAINER_ID)
            .query_items(
                query="SELECT i.id, i.published, i.title, i.summary FROM Items i ORDER BY i.published DESC",
                enable_cross_partition_query=True,
            )
        )
        return items
