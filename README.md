# Audio Pipeline Container

A container that runs a Python script to process a data pipeline.

## Setup

Assumnes that you'll be using a virtual environment.

```bash
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Trying it Out

```bash
python src/main.py
```


## Build the container

```bash
docker build --tag jamespeechly/audiopipeline .
```