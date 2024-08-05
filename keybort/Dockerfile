FROM python:3-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_ROOT_USER_ACTION=ignore

WORKDIR /keybort

RUN apt-get update
COPY ./requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt
COPY ./ ./