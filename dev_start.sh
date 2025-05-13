#!/bin/sh

docker compose -f docker-compose-dev.yaml up -d   

mode=dev uvicorn app.main:app --host 0.0.0.0 --port 8000
