#!/bin/bash

VERSION="v0.1.2"

cp .env.$1 .env

npm install
npm run build

cp config_prod.json dist/config.json
tar -czf clio-web-$VERSION.zip dist/*
