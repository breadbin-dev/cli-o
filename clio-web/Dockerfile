FROM nginx:latest

ARG BUILD

RUN mkdir -p /usr/share/nginx/html/clio-web
COPY $BUILD/ /usr/share/nginx/html/clio-web/
COPY nginx.conf /etc/nginx/conf.d/default.conf

RUN chmod -R 777 /usr/share/nginx/html/clio-web /etc/nginx/conf.d/default.conf

EXPOSE 80