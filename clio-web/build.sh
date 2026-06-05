#!/bin/bash

VERSION="v0.1.3"

npm install
npm run build

cp config.json dist/config.json
tar -czf clio-web-$VERSION.tar.gz dist/*

docker build --build-arg BUILD=dist -t clio-web:$VERSION .

docker tag clio-web:$VERSION iandennis/clio-web:$VERSION
docker push iandennis/clio-web:$VERSION