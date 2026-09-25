"""Thin reverse proxy: binds 0.0.0.0:<port> and forwards to the agentcore dev server on 127.0.0.1:8080."""
import http.server
import urllib.request
import os
import sys

UPSTREAM = "http://127.0.0.1:8080"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8501


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_request(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else None

        headers = {k: v for k, v in self.headers.items() if k.lower() not in ("host",)}
        req = urllib.request.Request(
            f"{UPSTREAM}{self.path}",
            data=body,
            headers=headers,
            method=self.command,
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                self.send_response(resp.status)
                for k, v in resp.getheaders():
                    if k.lower() not in ("transfer-encoding",):
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(str(e).encode())

    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_request

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", PORT), ProxyHandler)
    url = f"{os.environ.get('WORKSHOP_URL', 'http://localhost')}/app/{PORT}/"
    print(f"Proxy listening on 0.0.0.0:{PORT} → {UPSTREAM}")
    print(f"Access at: {url}")
    server.serve_forever()
