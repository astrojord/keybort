FROM node:22-bookworm-slim AS assets

WORKDIR /build

COPY ./package.json ./package-lock.json ./
RUN npm ci
COPY ./static ./static
COPY ./boards/templates ./boards/templates
RUN npm run build

FROM python:3.14-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_ROOT_USER_ACTION=ignore

WORKDIR /keybort

RUN apt-get update
COPY ./requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt
COPY ./ ./
COPY --from=assets /build/static/site.css /build/static/basecoat.min.js ./static/
