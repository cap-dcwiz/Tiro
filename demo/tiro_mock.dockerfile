FROM python:3.10-slim

WORKDIR /tiro

ENV PYTHONPATH="${PYTHONPATH}:/tiro/" \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

RUN pip install poetry
RUN poetry config virtualenvs.create false

COPY deps /tiro/deps
COPY pyproject.toml /tiro/
COPY tiro /tiro/tiro

RUN sed -i '/git/d' pyproject.toml
RUN pip install /tiro/deps/*.whl
RUN poetry install --no-dev

