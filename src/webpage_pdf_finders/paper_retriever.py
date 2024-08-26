import asyncio
import csv
import datetime
import io
import itertools
import json
import logging
import os
import re
import time

import aiofiles
import aiohttp
import redis.asyncio as redis
from aio_pika import IncomingMessage
from aiohttp import ClientResponse

from src import config
from src.webpage_pdf_finders.fake_proxy import FakeProxy

csv_lock = asyncio.Lock()

# proxy_manager = FreeProxy(https=True)
proxy_manager = FakeProxy(https=True)

logger = logging.getLogger("papers_searcher")
redis = redis.from_url(config.REDIS_URL)


async def fetch(url, session):
    try:
        logger.debug("Fetching %s", url)
        async with session.get(url, proxy=proxy_manager.get()) as response:
            response.raise_for_status()
            return await response.text()
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None


def extract_urls(html):
    url_pattern = re.compile(r'(https?://[^\s\'"<>]+)', re.IGNORECASE)
    return url_pattern.findall(html)


async def is_pdf_link(url, session):
    try:
        async with session.head(url) as response:
            if response.headers.get("Content-Type") == "application/pdf":
                return True
    except Exception:
        return False


async def load_pdf(url, session):
    try:
        async with session.get(url, proxy=proxy_manager.get()) as response:
            response
    except Exception:
        return False


async def find_pdfs(url, session, level=0, max_levels=4):
    if (data := await redis.get(url)) is not None:
        logger.debug("Cache hit for %s", url)
        return json.loads(data)

    if level > max_levels:
        return []

    html_content = await fetch(url, session)
    if html_content is None:
        return []

    urls_to_check = []
    urls = sorted(set(extract_urls(html_content)))
    logger.debug("Number of parsed urls for %s: %s", url, len(urls))
    for url in urls:
        if await is_pdf_link(url, session):
            logger.info("Pdf found, url: %s", url)
            await redis.set(url, json.dumps([url]))
            return [url]
        else:
            urls_to_check.append(url)
    logger.debug("Failed to find PDF, looking in nested links: %s", len(urls_to_check))

    nested_pdf = await asyncio.gather(find_pdfs(url, session, level + 1, max_levels) for url in urls_to_check)
    final_urls = list(itertools.chain.from_iterable(nested_pdf))
    await redis.set(url, json.dumps(final_urls))
    return final_urls


def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|\s]', "_", filename)


def parse_filename(response: ClientResponse):
    content_disposition = response.headers.get('Content-Disposition')
    if content_disposition:
        match = re.findall('filename="?([^"]+)"?', content_disposition)
        if match:
            return sanitize_filename(match[0])
    return sanitize_filename(os.path.basename(response.url.path))


async def find_and_load_by_url(url: str, destination: str, timeout: int = 60):
    headers = {
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    start_time = time.time()

    files = []

    async with aiohttp.ClientSession(headers=headers) as session:
        pdf_links = await asyncio.wait_for(find_pdfs(url, session), timeout)
        logger.info("Amount of found PDFs for %s: %s", url, len(pdf_links))
        for link in pdf_links:
            path = None
            try:
                async with session.get(link, proxy=proxy_manager.get()) as response:
                    response.raise_for_status()
                    filename = parse_filename(response)
                    if not filename.endswith(".pdf"):
                        filename += ".pdf"
                    path = destination + "/" + filename
                    async with aiofiles.open(path, mode="wb") as file:
                        data = await response.content.read()
                        await file.write(data)
                        logger.debug("PDF %s saved to %s", filename, destination)
            except Exception as exc:
                logger.error("Failed, error: " + str(exc))
            finally:
                files.append(path)
    logger.debug("Paper retrival took %s second(s)", time.time() - start_time)
    return pdf_links, files


async def write_to_csv(data):
    async with csv_lock:
        async with aiofiles.open(config.PDF_TARGET_LOCATION + '/loaded_pdfs.csv', mode='a', newline='') as file:
            output = io.StringIO()
            writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(data)
            await file.write(output.getvalue())


async def message_callback(message: IncomingMessage):
    async with message.process():
        data = json.loads(message.body.decode())
        logger.info("Incoming message for: %s", data['title'])
        success = True
        links = files = None
        try:
            links, files = await find_and_load_by_url(data['url'], config.PDF_TARGET_LOCATION, 180)
        except TimeoutError as exc:
            success = False
            logger.error("Timeout error for: %s", data['title'])
            raise exc
        finally:
            logger.info("Saving record info")
            await write_to_csv(
                [data['title'], data['url'], data['metadata'], datetime.datetime.now(), success, links, files]
            )


if __name__ == "__main__":
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)
    logger.info("Logging configured")
    doi = '10.30702/ujcvs/24.32(02)/LR024-113119'
    asyncio.run(find_and_load_by_url(doi, "./pdfs"))
