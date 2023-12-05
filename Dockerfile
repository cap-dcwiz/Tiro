FROM ghcr.io/cap-dcwiz/utinni:0.13.3 as build

ENV PYTHONPATH="${PYTHONPATH}:/opt/" \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

RUN pip install poetry
RUN poetry config virtualenvs.create false

WORKDIR /opt

COPY ./ /opt/
RUN apt-get update && apt-get upgrade -y && \
    apt-get install build-essential && \
    poetry install && poetry build -f wheel

FROM ghcr.io/cap-dcwiz/utinni:0.13.3

ENV PYTHONPATH="${PYTHONPATH}:/tiro/" \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

COPY --from=build /opt/dist/*.whl /opt

RUN apt-get update && apt-get upgrade -y && \
    apt-get install build-essential -y && \
    # for easier debugging in container
    apt-get install vim iputils-ping -y && \
    pip install *.whl && \
    apt-get purge build-essential -y &&  \
    rm -rf /var/lib/apt/lists/* && \
    rm /opt/*.whl

WORKDIR /tiro
