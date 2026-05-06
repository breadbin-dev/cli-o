#!/bin/bash

cp .env.$1 .env

npm install
npm run build

mv dist $1
