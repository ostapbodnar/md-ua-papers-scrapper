import json

import pika
from elsapy.elsclient import ElsClient
from elsapy.elssearch import ElsSearch
from pika.adapters.blocking_connection import BlockingChannel

from src import config
from src.queue_service import connect_to_channel

UA_PAPERS_SEARCH_QUERY = 'LANGUAGE ( ukrainian ) AND ( LIMIT-TO ( OA , "all" ) )'


def load_papers_identifiers(query: str):
    client = ElsClient(config.API_KEY)

    search = ElsSearch(query, 'scopus')
    search.execute(client)
    print("Paper count: ", len(search.results))

    with connect_to_channel(config.RABBIT_MQ_QUEUE_NAME) as channel:
        for doc in search.results:
            if 'dc:title' in doc and 'dc:identifier' in doc:

                title = doc['dc:title'].replace('/', '-')
                identifier = doc['prism:doi']
                print(f"Title: {title}")
                try:
                    trigger_paper_processing(channel, identifier, title)
                except Exception as exc:
                    print(f"Failed to download PDF for: {title} (Status Code: {exc})")

            else:
                print(f"Failed to retrieve full document for: {title}")


def trigger_paper_processing(channel: BlockingChannel, doi: str, title: str):
    url = f"https://doi.org/{doi}"
    message = json.dumps({"url": url, "title": title, }).encode()
    channel.basic_publish(exchange='',
                          routing_key=config.RABBIT_MQ_QUEUE_NAME,
                          body=message,
                          properties=pika.BasicProperties(
                              delivery_mode=2,
                          ))


if __name__ == "__main__":
    load_papers_identifiers(UA_PAPERS_SEARCH_QUERY)
