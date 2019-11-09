# Basic nginx configuration

When you install nginx from the debian repositories, it comes with a basic configuration to show that nginx is working. However, the out-of-the-box configuration does not set you up very well for a secure server that uses HTTPS only.

You can use this basic configuration as a template for your own setup. It contains a slightly altered `nginx.conf` that sets some security-relevant headers, configures secure defaults for HTTPS connections and also redirects users if they try to access your websites using HTTP.

First thing we need to do: We are going to need a version of nginx with a few extra features:

```bash
sudo apt install nginx-extras
```

Then merge our configuration into your nginx configuration directory and remove the pre-installed default site config:

```bash
sudo cp -RT /opt/pajbot/install-docs/full-nginx-setup/basic-config/ /etc/nginx/
sudo rm /etc/nginx/sites-{available,default}/default
```

We also need to generate a cryptographic file called the "Diffie-Hellman parameters":

```bash
sudo openssl dhparam -out /etc/ssl/certs/dhparam.pem 4096
```

This command can potentially take quite long (on the order of 1-2 hours if your CPU is not very recent).

> Note: Diffie-Hellman parameters are not secret in any sense (Your server even sends these parameters to connecting clients), so you don't need to keep the generated file secret, or worry about leaking it.

Once that's done, restart nginx like this:

```bash
sudo systemctl reload nginx
```
