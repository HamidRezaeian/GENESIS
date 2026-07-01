import http.server
import os

PUBLIC_DIR = os.path.abspath('public')

class MockReq:
    def makefile(self, *args, **kwargs):
        from io import BytesIO
        return BytesIO(b"GET / HTTP/1.0\r\n\r\n")
    def sendall(self, data):
        pass

class APIHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)
        
    def do_GET(self):
        print(f"do_GET called: path={self.path}, directory={self.directory}")
        if self.path == '/':
            self.path = '/index.html'
            return super().do_GET()
        else:
            return super().do_GET()

    def send_error(self, code, message=None, explain=None):
        print(f"Error {code}: {message}")
        super().send_error(code, message, explain)

handler = APIHandler(MockReq(), ('127.0.0.1', 12345), None)
