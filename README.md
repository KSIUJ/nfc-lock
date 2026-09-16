# nfc-lock
NFC door lock

## Installation

1. `apt install python3-pip python3-dev python3-systemd build-essential openssl`
2. `cd /opt/`
3. `git clone https://github.com/KSIUJ/nfc-lock`
4. `pip3 install -r requirements.txt --break-system-packages --ignore-installed`
   - `--ignore-installed` is required because current Raspberry Pi OS ships `rpi-lgpio` (apt-managed, no pip RECORD file) in place of `RPi.GPIO`, and pip can't uninstall it; this instead shadows it with the real `RPi.GPIO` this project needs on older boards.
   - `python3-dev` is required to compile `RPi.GPIO`'s C extension.
5. `mkdir -p cache cert`
6. Obtain the mTLS client certificate/key used to authenticate to ERC's origin (issued by whoever runs ERC) and place them at the paths configured in `erc['client_cert_file']` / `erc['client_key_file']` (e.g. `cert/erc-client.crt` / `cert/erc-client.key`)
7. `cp -r config-example/ config`, change relevant values in `config`, and set `config/erc_secret.py`'s `api_key` to the lock's `LOCK_API_KEY` from ERC
8. Create `/etc/systemd/system/nfc-lock.service`, contents below
9. `systemctl daemon-reload; systemctl enable nfc-lock; systemctl restart nfc-lock`

The lock only ever makes outbound HTTPS requests to ERC (`GET`/`POST` to `erc.ksi.sh`, authenticated with the API key plus the mTLS client certificate above) — it doesn't host anything itself, so no reverse proxy or inbound TLS setup is needed on this host.

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

