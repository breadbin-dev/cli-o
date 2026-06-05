# clio

**Command Line Interface — Online.** Deploy data science tools to the web without any UI work. Cli-o gives you a flexible, interactive interface accessible from a browser.
Simply write a standard python component with functions that return text, dataframes, charts, and Cli-o makes it available in a CLI driven web page.


## Installation

### clio-py
This is the python package:
```bash
pip install "git+https://github.com/breadbin-dev/cli-o.git#subdirectory=clio-py"
```
Or pin to a specific tag:
```bash
pip install "git+https://github.com/breadbin-dev/cli-o.git@vX.X.X#subdirectory=clio-py"
```
Simply create a class with functions that you want to expose to the command line.
Functions should have type-hints and pydocs as these will be converted into hints in the UI.
Then to host your component:
```python
router = RouterClient("[router_url]", "[router_token]")
my_component = MyComponent()
WidgetWrapper.host_object("my_commands", my_component, router)
```

For examples check out **demo.py** in the clio-py project.

## Development installation

The easiest way to work locally is to run the web and router docker images.

Simply run 'docker compose up' using this compose.yaml. And access the website through http://localhost:8080
```
services:
    clio-web:
      image: iandennis/clio-web:v0.1.3
      ports:
        - "8080:80"

    clio-services:
      image: iandennis/clio-services:v0.1.3
      ports:
        - "8085:85"     
```

These images are not suitable for production as they have authentication turned off.


## Production installation

### clio-web
Release clio-web-vX.X.X.tar.gz contains the web page deployment, this can be hosted with nginx.
Edit the contents of config.json with your title, router location (see below), colours etc.

### clio-router
Release clio-services-vX.X.X.tar.gz contains the command router, this connects the web page to your components.
Use root.properties as a template to create your \[service_user\].properties.
External web clients need to be able to hit this, so can also be proxied through nginx (see below).
Entitlements to commands can be added in entitlements.json.
If managing your own users, create a services api keys for your services.



### example nginx config
```
server {
   listen 80;

   location / {
       return 301 https://$host$request_uri;
   }

   access_log /var/log/nginx/http_access.log;
   error_log  /var/log/nginx/http_error.log;
}

server {
    listen 443 ssl ;
    ssl_certificate [your certificate]; 
    ssl_certificate_key [your certificate key];

    location / {
        root [your clio-web location];
    }

    location /api/ {
        proxy_pass http://localhost:85/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_read_timeout 1d;
    }

    access_log /var/log/nginx/https_access.log;
    error_log  /var/log/nginx/https_error.log;
}
```