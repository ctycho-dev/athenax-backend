#!/bin/sh

git restore .
git pull origin main

docker build . -t athenax-backend

docker-compose down
docker-compose up -d
