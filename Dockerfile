FROM python:3

LABEL org.opencontainers.image.authors="james@voiceactivesolutions.co.uk"
LABEL org.opencontainers.image.vendor="Voice Active Solutions Ltd."
LABEL org.opencontainers.image.description="An audio pipeline that takes a .WAV file containing speech and converts it to text."
LABEL org.opencontainers.image.version="1.0.5"

RUN mkdir -p /usr/src/app/logs
WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY /src ./

CMD [ "python", "./main.py" ]
