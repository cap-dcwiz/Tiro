FROM python:3.10

WORKDIR /tiro

ENV PYTHONPATH="${PYTHONPATH}:/tiro/" \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

RUN pip install poetry
RUN poetry config virtualenvs.create false

COPY pyproject.toml /tiro/
COPY deps/ /tiro/deps/
COPY tiro /tiro/tiro

RUN apt-get update && apt-get upgrade -y &&  \
    apt-get install build-essential graphviz graphviz-dev -y &&  \
    poetry install -vvv --no-dev --no-interaction --no-ansi && \
    pip install deps/*.whl && \
    apt-get purge build-essential -y  &&  rm -rf /var/lib/apt/lists/* && \
    rm /tiro/poetry.lock /tiro/pyproject.toml

