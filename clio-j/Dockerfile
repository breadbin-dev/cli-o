FROM eclipse-temurin:21-jre

ARG SERVICES_BUILD

COPY $SERVICES_BUILD .
RUN mkdir /root/clio-services
RUN tar -xzf $SERVICES_BUILD -C /root/clio-services/ --no-same-owner
RUN rm $SERVICES_BUILD

ENV USER=container

ENTRYPOINT ["java", "-cp", "/root/clio-services/lib/*:/root/clio-services/resources/*", "clio.router.RouterMain"]