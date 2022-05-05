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
    TAGS = ['span', 'p', 'a']

    def __init__(self):
        self.logger = logging
        self.error = ''
        self.data = ''
        self.content_type = ''
        self.status_code = 200

    def _error(self, message):
        self.error = message
        self.logger.error(message)

    def fetch_data(self, url):
        response = urllib.request.urlopen(ROOT_URL + url)
        self.logger.info(f"Data fetched from {ROOT_URL + url}")
        return response

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
        span_arr = soup.find_all(self.TAGS)
        for element_arr in span_arr:
            for el in element_arr:
                el.string = self.PATTERN.sub(self.SUBST, el.text)
        return soup

    def start(self, url):
        # Fetch data
        response = self.fetch_data(url)
        if not response:
            return False
        # Set content type
        if not self._set_content_type(response):
            return False
        # Set status code
        if not self._set_status_code(response):
            return False
        # Parse response with Beautiful soup
        soup = self.parse_response(response)
        if not soup:
            return False
        # Customize response
        custom_response = self.customize_response(soup)
        if not custom_response:
            return False
        return custom_response


class MyProxy(SimpleHTTPServer.SimpleHTTPRequestHandler):
    custom_response = ProxyParameter()

    def do_GET(self):
        url = self.path
        custom_html = self.custom_response.start(url)
        self.send_response(self.custom_response.status_code)
        self.send_header("Content-type", self.custom_response.content_type)
        self.end_headers()
        self.wfile.write(custom_html.prettify().encode())


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
