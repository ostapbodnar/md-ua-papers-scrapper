import json
import logging

import pika
from elsapy.elsclient import ElsClient
from elsapy.elssearch import ElsSearch
from pika.adapters.blocking_connection import BlockingChannel

from src import config
from src.queue_service import connect_to_channel
from src.webpage_pdf_finders.utils import generate_year_pairs

UA_PAPERS_SEARCH_QUERY_PATTERN = 'LANGUAGE ( ukrainian ) {year} AND ( LIMIT-TO ( OA , "all" ) )'


class ExtendedElsSearch(ElsSearch):

    def execute_gen(
            self,
            els_client=None,
            get_all=False,
            use_cursor=False,
            view=None,
    ):
        """Executes the search. If get_all = False (default), this retrieves
            the default number of results specified for the API. If
            get_all = True, multiple API calls will be made to iteratively get
            all results for the search, up to a maximum of 5,000."""
        url = self._uri
        if use_cursor:
            url += "&cursor=*"
        if view:
            url += "&view={}".format(view)
        api_response = els_client.exec_request(url)
        _tot_num_res = int(api_response['search-results']['opensearch:totalResults'])
        _results = api_response['search-results']['entry']
        num_res = len(_results)
        yield _results, num_res, _tot_num_res
        if get_all is True:
            while (num_res < _tot_num_res) and not num_res >= 5000:
                for e in api_response['search-results']['link']:
                    if e['@ref'] == 'next':
                        next_url = e['@href']
                api_response = els_client.exec_request(next_url)
                res = api_response['search-results']['entry']
                num_res += len(res)
                yield res, num_res, _tot_num_res


def load_papers_identifiers(query: str):
    logging.info(f"Loading papers for: {query}")
    client = ElsClient(config.API_KEY)

    search = ExtendedElsSearch(query, 'scopus')

    with connect_to_channel(config.RABBIT_MQ_QUEUE_NAME) as channel:

        for res, current_prog, total in search.execute_gen(client, get_all=True):
            logging.info("Paper count: %s/%s", current_prog, total)
            for i, doc in enumerate(res):
                if 'dc:title' in doc and 'prism:doi' in doc:

                    title = doc['dc:title'].replace('/', '-')
                    identifier = doc['prism:doi']
                    logging.info(f"Title: {title}")
                    try:
                        trigger_paper_processing(channel, identifier, title, doc)
                    except Exception as exc:
                        logging.info(f"Failed to download PDF for: {title} (Status Code: {exc})")

                else:
                    logging.info(f"Failed to retrieve full document for: {current_prog + i}")


def trigger_paper_processing(channel: BlockingChannel, doi: str, title: str, meta: dict):
    url = f"https://doi.org/{doi}"
    message = json.dumps({"url": url, "title": title, "metadata": meta}).encode()
    channel.basic_publish(exchange='',
                          routing_key=config.RABBIT_MQ_QUEUE_NAME,
                          body=message,
                          properties=pika.BasicProperties(
                              delivery_mode=2,
                          ))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    for start, end in generate_year_pairs(2000, 2025)[::-1]:
        query = f"AND PUBYEAR > {start - 1} AND PUBYEAR < {end + 1}"
        load_papers_identifiers(UA_PAPERS_SEARCH_QUERY_PATTERN.format(year=query))
