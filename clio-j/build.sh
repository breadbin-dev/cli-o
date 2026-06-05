#!/bin/bash

VERSION=v0.1.3
TARGET=clio-services-$VERSION.tar.gz

rm -rf deploy/
rm -rf **/deploy/
mvn -B -DskipTests -Drevision=$VERSION clean install

mkdir -p deploy/resources
cp **/src/main/resources/* deploy/resources/

mkdir -p deploy/lib
mvn dependency:copy-dependencies -Drevision=$VERSION -DoutputDirectory=deploy/lib
cp */target/*.jar deploy/lib/

cd deploy
tar -czf ../$TARGET ./*
cd ..

docker build --build-arg SERVICES_BUILD=$TARGET -t clio-services:$VERSION .

docker tag clio-web:$VERSION iandennis/clio-services:$VERSION
docker push iandennis/clio-services:$VERSION