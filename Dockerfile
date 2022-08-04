FROM python:3.9-slim
LABEL maintainer="adamrussak@gmail.com & tomer.klein@gmail.com"
ENV PYTHONIOENCODING=utf-8
ENV LANG=C.UTF-8
ENV GEO_IP_URL ""
ENV DB_USER ""
ENV DB_PASS ""
ENV DB_HOST ""
ENV DB_PORT ""
ENV GRAFANA_DB_NAME ""
ENV GRAFANA_TABLE_NAME ""
ENV SLEEP_TIME ""
ENV LOG_PATH ""

RUN mkdir -p /opt/geo-logger

WORKDIR /opt/geo-logger

COPY requirements.txt ./
RUN apt-get update -y \
    && pip install --upgrade pip \
    && python3 -m pip install --no-cache-dir -r requirements.txt

COPY geo-logger /opt/geo-logger

CMD [ "python", "/opt/geo-logger/logger.py" ]