#!/bin/bash

poetry export --without-hashes -f requirements.txt -o requirements.txt
gcloud app deploy app.yaml
