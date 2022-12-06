FROM python:3.7-slim

WORKDIR /app

COPY . /app
RUN apt-get -y update  && apt-get install -y \
  gcc \
  python3-dev \
  apt-utils \
  python-dev \
  build-essential \
&& rm -rf /var/lib/apt/lists/*

EXPOSE 8050/tcp

COPY requirements.txt /tmp/
COPY ./app /app
WORKDIR "/app"
RUN pip install -r /tmp/requirements.txt
ENTRYPOINT [ "python3" ]
CMD [ "main.py" ]