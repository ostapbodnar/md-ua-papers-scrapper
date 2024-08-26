import os
from pathlib import Path

API_KEY = os.getenv("ELSAVIER_API_KEY")
RABBIT_MQ_HOST = os.getenv("RABBIT_MQ_HOST", 'localhost')
RABBIT_MQ_PORT = int(os.getenv("RABBIT_MQ_PORT", 5672))
RABBIT_MQ_QUEUE_NAME = os.getenv("RABBIT_MQ_QUEUE_NAME", 'papers_identifiers')
PDF_TARGET_LOCATION = os.getenv("PDF_TARGET_LOCATION", str(Path(__file__).parent.parent / "pdfs"))

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
