# nfc-lock
NFC door lock

## Installation

1. `apt install python3-pip python3-systemd build-essential openssl`
2. `cd /opt/`
3. `git clone https://github.com/KSIUJ/nfc-lock`
4. `pip3 install -r requirements.txt`
6. `mkdir crt`
7. `openssl req -x509 -newkey rsa:4096 -keyout cert/$(hostname).key -out cert/$(hostname).crt -nodes -days 365` 
5. `cp -r config-example/ config`, change relevant values in `config`
6. Create `/etc/systemd/system/nfc-lock.service`, contents below
7. `systemctl daemon-reload; systemctl restart nfc-lock`

`/etc/systemd/system/nfc-lock.service`:
```
[Unit]
Description=NFC door lock
After=multi-user.target

[Service]
Type=simple
WorkingDirectory=/opt/nfc-lock
ExecStart=/usr/bin/python3 -u /opt/nfc-lock/app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Remember to adjust `WorkingDirectory` and `ExecStart`

