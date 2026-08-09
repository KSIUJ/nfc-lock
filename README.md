# nfc-lock
NFC door lock

## Installation

1. `apt install python3-pip python3-dev python3-systemd build-essential openssl`
2. `cd /opt/`
3. `git clone https://github.com/KSIUJ/nfc-lock`
4. `pip3 install -r requirements.txt --break-system-packages --ignore-installed`
   - `--ignore-installed` is required because current Raspberry Pi OS ships `rpi-lgpio` (apt-managed, no pip RECORD file) in place of `RPi.GPIO`, and pip can't uninstall it; this instead shadows it with the real `RPi.GPIO` this project needs on older boards.
   - `python3-dev` is required to compile `RPi.GPIO`'s C extension.
5. `mkdir cert`
6. Obtain the mTLS client certificate/key used to authenticate to Keycloak's origin (issued by whoever runs Keycloak) and place them at the paths configured in `keycloak['client_cert_file']` / `keycloak['client_key_file']` (e.g. `cert/keycloak-client.crt` / `cert/keycloak-client.key`)
7. `cp -r config-example/ config`, change relevant values in `config`
8. Set up nginx as a reverse proxy in front of the app to terminate TLS for the remote-unlock API (see below)
9. Create `/etc/systemd/system/nfc-lock.service`, contents below
10. `systemctl daemon-reload; systemctl enable nfc-lock; systemctl restart nfc-lock`

### nginx TLS termination

The app itself only listens on plain HTTP at `127.0.0.1:8000` (see `server['port']` in `config/main.py`). nginx is responsible for terminating TLS and proxying to it, e.g.:

```
server {
    listen 443 ssl;
    server_name lock.internal.ksi.sh;

    ssl_certificate     /etc/letsencrypt/live/lock.internal.ksi.sh/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lock.internal.ksi.sh/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

Adjust `server_name`/cert paths to your setup (self-signed certs work too, just swap `ssl_certificate*` for your own files).

### Reader-link web page

`web/index.html` is a static page (see it for source) that shows the last-scanned UID live and lets you copy it or clear the auth cache, without ever exposing `server_secret.api_token` to the browser — nginx injects the token server-side when proxying `/api/*` to the app:

```
server {
    listen 443 ssl;
    server_name lock.internal.ksi.sh;

    ssl_certificate     /etc/letsencrypt/live/lock.internal.ksi.sh/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lock.internal.ksi.sh/privkey.pem;

    root /opt/nfc-lock/web;
    index index.html;

    location /api/last-uid {
        proxy_pass http://127.0.0.1:8000/last-uid?token=REPLACE_WITH_API_TOKEN;
    }

    location /api/clear-cache {
        proxy_pass http://127.0.0.1:8000/clear-cache?token=REPLACE_WITH_API_TOKEN;
    }

    location / {
        try_files $uri $uri/ =404;
    }
}
```

`REPLACE_WITH_API_TOKEN` must match `server_secret.api_token`. This can share the same `server{}` block as the reverse proxy above, or run on its own `server_name`/port if you'd rather keep the page and the raw unlock API separate.

`/etc/systemd/system/nfc-lock.service`:
```
[Unit]
Description=NFC door lock
After=multi-user.target

[Service]
Type=simple
Environment=REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
WorkingDirectory=/opt/nfc-lock
ExecStart=/usr/bin/python3 -u /opt/nfc-lock/app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Remember to adjust `WorkingDirectory` and `ExecStart`

