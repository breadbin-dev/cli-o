#!/bin/bash

cp .env.$1 .env

npm install
npm run build

cp config_prod.json dist/config.json
zip -r release.zip dist/
