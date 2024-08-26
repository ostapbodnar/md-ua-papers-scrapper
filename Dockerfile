FROM python:3.12-slim AS base
LABEL authors="ostapbodnar"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y curl \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && apt-get remove -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml poetry.lock /app/
RUN poetry config virtualenvs.create false && poetry install --no-dev
ENV PYTHONPATH="."

COPY ./src /app/src

FROM base AS scopus_paper_searcher

ENTRYPOINT ["python", "/app/src/paper_finders/scopus_paper_searcher.py"]

FROM base AS paper_scrapper

ENTRYPOINT ["python", "/app/src/webpage_pdf_finders/main.py"]
