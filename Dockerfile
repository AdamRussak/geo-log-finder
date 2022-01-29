FROM python:3.9-slim
LABEL maintainer="adamrussak@gmail.com"
ENV PYTHONIOENCODING=utf-8
ENV LANG=C.UTF-8
ENV logLocation ""
ENV dbUser ""
ENV dbPass ""
ENV dbHost ""
ENV dbPort ""
ENV dbName ""
ENV geoIpUrl ""
ENV sleepTime ""
WORKDIR /usr/src/app

COPY requirements.txt ./
RUN apt-get update -y \
    && apt-get install -y gcc libmariadb-dev  \
    && pip install --upgrade pip \
    && pip install discord \
    && python3 -m pip install --no-cache-dir -r requirements.txt
RUN pwd && ls -alh
COPY Ip_Map.py ./

CMD [ "python", "/usr/src/app/Ip_Map.py" ]