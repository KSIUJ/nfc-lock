from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer
import ssl
from urllib.parse import urlparse,parse_qs
from threading import Thread

import config.main as config

class RequestHandler(BaseHTTPRequestHandler):
    openingLock = None
    password = None

    def __init__(self, password, openingLock, *args, **kwargs):
        self.openingLock = openingLock
        self.password = password
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


    def do_GET(self):
        urlParsed = urlparse(self.path)
        paramParsed = parse_qs(urlParsed.query)
        #Testing parameters "pass" and "password"
        if ('pass' in paramParsed and paramParsed['pass'][0] == self.password) or ('password' in paramParsed and paramParsed['password'][0] == self.password):
            self.sendResponse(code=200)
            self.openingLock()
        else:
            self.sendResponse(code=403)


class Server:
    def start(self, password, openingLock, addr = '', port = 8000):
        httpd = HTTPServer((addr, port), partial(RequestHandler, password, openingLock))
        httpd.socket = ssl.wrap_socket (httpd.socket, keyfile=config.server['key_file'], certfile=config.server['cert_file'], server_side=True)
        Thread(target=httpd.serve_forever).start()
