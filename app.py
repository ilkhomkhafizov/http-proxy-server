import re
import logging
import socketserver
import http.server as SimpleHTTPServer

from bs4 import BeautifulSoup
import urllib.request
from decouple import config

PORT = config('PORT', cast=int)
ROOT_URL = config('BASE_URL', cast=str)
LETTERS_NUMBER = config('LETTERS_NUMBER', cast=int)
SYMBOL = config('SYMBOL', cast=str)


class ProxyParameter:
    PATTERN = re.compile(r"\b(\w{%d})\b" % LETTERS_NUMBER)
    SUBST = "\\1%s" % SYMBOL

    def __init__(self):
        self.logger = logging
        self.error = ''
        self.content_type = 'text/html'
        self.status_code = 404
        self.response = b"Page Not Found"

    def _error(self, message):
        self.error = message
        self.logger.error(message)

    def fetch_data(self, url):
        try:
            response = urllib.request.urlopen(ROOT_URL + url)
            self.logger.info(f"Data fetched from {ROOT_URL + url}")
            return response
        except Exception as error:
            self.logger.error("Can't open url", error)
            return False

    def _set_content_type(self, response):
        self.content_type = response.getheader('content-type')
        return True

    def _set_status_code(self, response):
        self.status_code = response.status
        return True

    def parse_response(self, response):
        try:
            soup = BeautifulSoup(response.read(), 'html.parser')
            return soup
        except Exception as error:
            self.logger.error("Error on parse", error)
            return False

    def customize_response(self, soup):
        find_text = soup.find_all(text=self.PATTERN)
        for text_el in find_text:
            fixed_text = self.PATTERN.sub(self.SUBST, text_el)
            text_el.replace_with(fixed_text)
        return soup.prettify().encode()

    def start(self, url):
        # Fetch data
        response = self.fetch_data(url)
        if not response:
            return self.response
        # Set content type
        if not self._set_content_type(response):
            return False
        # Set status code
        if not self._set_status_code(response):
            return False
        # Parse response with Beautiful soup
        if not ('.js' in response.url or '.css' in response.url or '.gif' in response.url or '.jpg' in response.url):
            soup = self.parse_response(response)
            custom_response = self.customize_response(soup)
            return custom_response
        return response.read()


class MyProxy(SimpleHTTPServer.SimpleHTTPRequestHandler):
    custom_response = ProxyParameter()

    def do_GET(self):
        url = self.path
        custom_html = self.custom_response.start(url)
        self.send_response(self.custom_response.status_code)
        self.send_header("Content-type", self.custom_response.content_type)
        self.end_headers()
        self.wfile.write(custom_html)


class Server:
    def __init__(self):
        self.proxy = MyProxy
        self.socket_server = socketserver.ForkingTCPServer(('', PORT), self.proxy)

    def run(self):
        print(f"Socket server started on port {PORT}")
        self.socket_server.serve_forever()


if __name__ == '__main__':
    server = Server()
    server.run()
