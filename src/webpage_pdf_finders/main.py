import asyncio
import logging

from src.queue_service import consume_messages_async
from src.webpage_pdf_finders.paper_retriever import message_callback

if __name__ == '__main__':
    logger = logging.getLogger("papers_searcher")
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)
    logger.info("Logging configured")
    asyncio.run(consume_messages_async(message_callback))
