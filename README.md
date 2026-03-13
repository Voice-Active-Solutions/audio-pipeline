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

## Build the container image

You need to make sure that you use a multiarch builder, as IBM CodeEngine will complain unless your image uses `linux/amd64` as the architecture. The easiest way to get around this is to your the `docker buildx build` command. A script `build-image.sh` can be used for this purpose. It pushes the resulting `jamespeechly/audiopipeline` image to the Docker repository. From here it can be used by Code Engine.

### Versioning the image

The version of the application is set in the `_version.py` file. It's recommended that you tag releases when you increment this file, for example:

```bash
git tag v1.0.5
git push --all-tags
```
