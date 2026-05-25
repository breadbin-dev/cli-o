#!/bin/bash

VERSION=v0.1.2
TARGET=clio-services-$VERSION.tar.gz

mvn -B -DskipTests -Drevision=$VERSION clean install

mkdir -p deploy/resources
cp **/src/main/resources/* deploy/resources/

mkdir -p deploy/lib
mvn dependency:copy-dependencies -Drevision=$VERSION -DoutputDirectory=deploy/lib

cd deploy
tar -czf ../$TARGET ./*
cd ..
