FROM python:3.10-slim

WORKDIR /tiro

ENV PYTHONPATH="${PYTHONPATH}:/tiro/" \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

RUN pip install poetry
RUN poetry config virtualenvs.create false

COPY pyproject.toml /tiro/
COPY deps /tiro/deps
COPY tiro /tiro/tiro
RUN poetry install --no-dev