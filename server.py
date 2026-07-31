from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer
import hmac
import json
import ssl
from urllib.parse import urlparse,parse_qs
from threading import Thread

import config.main as config

class RequestHandler(BaseHTTPRequestHandler):
    openingLock = None
    password = None
    api_token = None
    last_scan = None

    def __init__(self, password, openingLock, api_token, last_scan, *args, **kwargs):
        self.openingLock = openingLock
        self.password = password
        self.api_token = api_token
        self.last_scan = last_scan
        super().__init__(*args, **kwargs)


    def sendResponse(self, code, message = None):
        self.send_response(code)
        self.send_header('Content-type','text/html')
        self.end_headers()
        if message is None:
            if code == 200:
                self.wfile.write(b"OK! Lock is opening.")
            if code == 403:
                self.wfile.write(b"Acces denied")
        else:
            self.wfile.write(bytes(message))


    def sendJson(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(body)


    def do_GET(self):
        urlParsed = urlparse(self.path)
        paramParsed = parse_qs(urlParsed.query)

        if urlParsed.path == '/last-uid':
            token = paramParsed.get('token', [''])[0]
            if hmac.compare_digest(token, self.api_token):
                self.sendJson(200, {'uid': self.last_scan.get('uid')})
            else:
                self.sendResponse(code=403)
            return

        #Testing parameters "pass" and "password"
        if ('pass' in paramParsed and paramParsed['pass'][0] == self.password) or ('password' in paramParsed and paramParsed['password'][0] == self.password):
            self.sendResponse(code=200)
            self.openingLock()
        else:
            self.sendResponse(code=403)


class Server:
    def __init__(self):
        self.last_scan = {'uid': None}

    def set_last_uid(self, uid):
        self.last_scan['uid'] = uid

    def start(self, password, openingLock, api_token, addr = '', port = 8000):
        httpd = HTTPServer((addr, port), partial(RequestHandler, password, openingLock, api_token, self.last_scan))
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=config.server['cert_file'], keyfile=config.server['key_file'])
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        Thread(target=httpd.serve_forever).start()
