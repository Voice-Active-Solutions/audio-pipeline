FROM python:3

RUN mkdir -p /usr/src/app/logs
WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY /src ./

CMD [ "python", "./main.py" ]
