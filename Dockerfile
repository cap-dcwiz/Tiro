FROM python:3.10

WORKDIR /tiro

ENV PYTHONPATH="${PYTHONPATH}:/tiro/" \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

RUN pip install poetry
RUN poetry config virtualenvs.create false

COPY pyproject.toml /tiro/
COPY tiro /tiro/tiro

RUN poetry install --no-dev &&  \
    rm /tiro/poetry.lock &&  \
    rm /tiro/pyproject.toml

