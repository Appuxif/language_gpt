FROM python:3.10.11-buster
RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get install -y ffmpeg

RUN mkdir -p /home/project/project
WORKDIR /home/project/project
RUN groupadd -r project && useradd -r -g project project
RUN chown project: /home/project -R
USER project

ENV VIRTUAL_ENV=/home/project/project/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install -U pip
RUN pip install poetry==1.4.0

COPY ./poetry.lock /home/project/project
COPY ./pyproject.toml /home/project/project
RUN poetry install --only main -n -v --no-root --no-cache

COPY . /home/project/project
