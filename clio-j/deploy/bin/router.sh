#!/bin/bash

JAVAHOME="/root/deploy/jdk-21.0.1"
DEPLOYMENT="/root/deploy/router"
CURRENT="$DEPLOYMENT/current"

LOG="$DEPLOYMENT/logs/router.log"
JAVACP="$CURRENT/classes/:$CURRENT/resources/:$CURRENT/lib/*"

exec $JAVAHOME/bin/java -cp $JAVACP -XX:+UseZGC -Xmx1G clio.router.RouterMain >> $LOG 2>&1 &