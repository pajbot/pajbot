# Certbot with CloudFlare DNS

In this small sub-guide, we will get a certificate from [Let's Encrypt](https://letsencrypt.org/), and we will use CloudFlare's API to add/remove DNS records to validate our ownership of the domain.

## Generate an API token for CloudFlare

<!--
This is commented out for now.
Generating API tokens like this would be better in the future, but the CloudFlare DNS Certbot plugin does not support it as of the time of writing this guide.
Once the feature is implemented (track https://github.com/certbot/certbot/issues/7252) **and** the release is in debian stable, we can switch to this version

- Navigate to https://dash.cloudflare.com/profile/api-tokens
- Under "API Tokens", click "Create Token"
- Enter a descriptive token name, e.g. "Certbot on my-server-name"
- In the "Permissions" row, select "Zone", "DNS", "Edit"
- In the "Zone Resources" row, select "Include", "Specific Zone", and select the domain you want to get the certificate for
- If you want your server to get access to more than one domain only, click "Add More" under "Zone Resources" and repeat for other zones.
- Click "Continue to Summary" when you're done, and verify what it shows is what you want
- Click "Create Token" to finally get your token!
- On the final page, copy the token and temporarily store it somewhere safe, or keep the page open. We will need this token in the next step.
-->

- Navigate to https://dash.cloudflare.com/profile/api-tokens
- Next to "Global API Key", click "View".
- Copy the token that's shown. We will need this token in the next step.

## Install Certbot

Certbot is a service that runs on your server that automatically takes care of requesting certificates (and keeping them refreshed) for your domains.

```bash
sudo apt install certbot python3-certbot-dns-cloudflare
```

## Store CloudFlare API token on the server

Create a file to hold your secret API key like this:

```bash
sudo mkdir -p /etc/letsencrypt/secrets
sudo cp /opt/pajbot/install-docs/certbot-with-cloudflare/cloudflare.ini /etc/letsencrypt/secrets/cloudflare.ini
sudo chown root:root /etc/letsencrypt/secrets/cloudflare.ini
sudo chmod 600 /etc/letsencrypt/secrets/cloudflare.ini
```

Then insert your API details:

```bash
sudo nano /etc/letsencrypt/secrets/cloudflare.ini
```

Put your CloudFlare account email next to `dns_cloudflare_email`, and the API key from the previous step next to `dns_cloudflare_api_key`.

## Request certificate with certbot

Repeat `-d "domain-name.com"` as many times as needed to add domain names and wildcards to your certificate.

```bash
sudo certbot certonly --dns-cloudflare --dns-cloudflare-credentials /etc/letsencrypt/secrets/cloudflare.ini -d "your-domain.com" -d "*.your-domain.com" --post-hook "systemctl reload nginx"
```

You should see output similar to this:

<pre><code>Saving debug log to /var/log/letsencrypt/letsencrypt.log
Plugins selected: Authenticator dns-cloudflare, Installer None
Obtaining a new certificate
Performing the following challenges:
dns-01 challenge for example.com
Waiting 10 seconds for DNS changes to propagate
Waiting for verification...
Cleaning up challenges

IMPORTANT NOTES:
 - Congratulations! Your certificate and chain have been saved at:
   <b>/etc/letsencrypt/live/your-domain.com/fullchain.pem</b>
   Your key file has been saved at:
   <b>/etc/letsencrypt/live/your-domain.com/privkey.pem</b>
   Your cert will expire on 2020-02-01. To obtain a new or tweaked
   version of this certificate in the future, simply run certbot
   again. To non-interactively renew *all* of your certificates, run
   "certbot renew"
 - If you like Certbot, please consider supporting our work by:

   Donating to ISRG / Let's Encrypt:   https://letsencrypt.org/donate
   Donating to EFF:                    https://eff.org/donate-le</code></pre>

Notice the highlighted part: This is important for setting up your nginx configuration: The first path is what goes with `ssl_certificate`, the second path goes with `ssl_certificate_key`.

You can now edit the nginx configuration file and point it to the correct certificate path:

```bash
sudo nano /etc/nginx/sites-available/streamer_name.your-domain.com.conf
```

```
ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
```

> Note! If you have requested a wildcard certificate (as we have done here in the example), you can re-use the same certificate for multiple bots.
> E.g. if you have bots running under the two subdomains `streamer_a.your-domain.com` and `streamer_b.your-domain.com`, and you have a wildcard certificate for `*.your-domain.com`, then both these site configurations can share the same certificate (`/etc/letsencrypt/live/your-domain.com/fullchain.pem` for example).
