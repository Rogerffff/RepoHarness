"""P4 public repro: scrapy 75450e75 (base 26ebdbf4efd5). Written from the public prompt only (E06).

Prompt: `scrapy shell -c "fetch('<url>')" --set TWISTED_REACTOR=...AsyncioSelectorReactor`
fails with "RuntimeError: There is no current event loop in thread 'Thread-1'".
Inference: the prompt's http://localhost/html is replaced by a throwaway HTTP server on
127.0.0.1 (loopback works without network); the shell runs as a subprocess from a temp cwd.
"""
import http.server, subprocess, sys, tempfile, threading
import scrapy

ERR = "There is no current event loop"


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"<html><body><p>ok</p></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def main():
    print("SCRAPY_FILE", scrapy.__file__, getattr(scrapy, "__version__", "?"))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/html"
    reactor = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
    cmd = [sys.executable, "-m", "scrapy.cmdline", "shell", "-c", f"fetch('{url}')",
           "--set", f"TWISTED_REACTOR={reactor}"]
    with tempfile.TemporaryDirectory() as d:
        try:
            p = subprocess.run(cmd, cwd=d, stdin=subprocess.DEVNULL, capture_output=True, timeout=45)
            rc, err = p.returncode, p.stderr.decode(errors="replace")
        except subprocess.TimeoutExpired as e:
            rc, err = "timeout", (e.stderr or b"").decode(errors="replace")
    srv.shutdown()
    print("SHELL_RC", rc)
    print("SHELL_CRAWLED_200", "Crawled (200)" in err)
    for line in [l for l in err.splitlines() if "rror" in l or "Crawled" in l][-8:]:
        print("STDERR|", line[:200])
    observed = ERR in err
    print(f"REPRO_OBSERVED={int(observed)}")
    if not observed:
        print("REPRO_REASON=no 'no current event loop' RuntimeError in the shell's stderr")
    return 0


if __name__ == "__main__":
    sys.exit(main())
