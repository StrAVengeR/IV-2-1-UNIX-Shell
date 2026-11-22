#!/usr/bin/env python3
"""Локал сервер: нэг osh session барина, Process tree-г бүртгэлээс байгуулна.
Зөвхөн өөрийн компьютер дээр ашиглана (бодит shell команд ажиллуулдаг)."""
import json, os, signal, subprocess, tempfile, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OSH = os.path.join(ROOT, "osh")
PORT = 8765
ALLOWED_HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
ALLOWED_ORIGINS = {f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"}


class Gen:
    """Нэг osh процессын төлөв. Reset хийхэд шинээр үүснэ, хуучин өгөгдөл холилдохгүй."""
    def __init__(self):
        self.segments = []      # command k-ийн (гаралт, exit code), дарааллаар
        self.buf = b""
        self.started = False    # эхний (асах үеийн) READY ирсэн эсэх
        self.eof = False
        self.sent = 0           # илгээсэн командын тоо
        self.history = []
        self.cv = threading.Condition()
        self.logpath = tempfile.mktemp(prefix="osh-", suffix=".jsonl")
        self.p = None


class Session:
    def __init__(self):
        self.lock = threading.Lock()
        self.g = None
        self.start()

    def start(self):
        g = Gen()
        env = dict(os.environ, OSH_LOG=g.logpath, OSH_PROTO="1")
        # start_new_session: Reset хийхэд бүх бүлгийг (хүүхдүүдтэй хамт) killpg-ээр зогсооно
        g.p = subprocess.Popen([OSH], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, env=env, bufsize=0,
                               start_new_session=True)
        threading.Thread(target=self.reader, args=(g,), daemon=True).start()
        with g.cv:
            g.cv.wait_for(lambda: g.started or g.eof, timeout=5)
        self.g = g

    @staticmethod
    def reader(g):
        fd = g.p.stdout.fileno()
        while True:
            try:
                d = os.read(fd, 4096)
            except OSError:
                d = b""
            with g.cv:
                if not d:
                    g.eof = True
                    g.cv.notify_all()
                    break
                g.buf += d
                while True:
                    i = g.buf.find(b"\x01READY ")
                    j = g.buf.find(b"\n", i) if i >= 0 else -1
                    if i < 0 or j < 0:
                        break
                    out = g.buf[:i]
                    try:
                        code = int(g.buf[i + 7:j] or 0)
                    except ValueError:
                        code = 0
                    g.buf = g.buf[j + 1:]
                    if g.started:
                        g.segments.append((out.decode("utf-8", "replace"), code))
                    else:
                        g.started = True
                    g.cv.notify_all()

    def run(self, line):
        line = " ".join(line.splitlines())
        with self.lock:
            g = self.g
            if g.eof or g.p.poll() is not None:
                self.start()
                g = self.g
            idx = g.sent
            g.sent += 1
            try:
                g.p.stdin.write((line + "\n").encode("utf-8"))
            except (BrokenPipeError, OSError):
                g.eof = True
            with g.cv:
                g.cv.wait_for(lambda: len(g.segments) > idx or g.eof, timeout=20)
                if len(g.segments) > idx:
                    out, code, timeout = g.segments[idx][0], g.segments[idx][1], False
                else:
                    out, code, timeout = "", None, True
            if line.strip():
                g.history.append(line)
            return {"output": out, "code": code,
                    "ended": g.eof or g.p.poll() is not None, "timeout": timeout}

    def reset(self):
        # Урт команд (run) түгжээг барьж байгаа тул эхлээд процессыг шууд зогсооно,
        # дараа нь түгжээ авч шинэ session эхлүүлнэ.
        g = self.g
        if g.p.poll() is None:
            try:
                os.killpg(g.p.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        try:
            g.p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        with self.lock:
            self.start()

    def tree(self):
        g = self.g
        procs, cmds, shell = {}, {}, None
        events = []
        try:
            with open(g.logpath, encoding="utf-8", errors="replace") as f:
                for l in f:
                    if l.strip():
                        try:
                            events.append(json.loads(l))
                        except ValueError:
                            pass
        except OSError:
            pass
        for e in events:
            if e.get("ev") == "shell":
                shell = e.get("pid")
            elif e.get("ev") == "spawn":
                procs[e["pid"]] = {"pid": e["pid"], "cmd": e["cmd"], "bg": e["bg"], "seq": e["seq"],
                                   "state": "running", "code": None, "t": e["t"]}
                cmds.setdefault(e["seq"], e["line"])
            elif e.get("ev") == "exit" and e["pid"] in procs:
                procs[e["pid"]].update(state="exited", code=e["code"])
        for p in procs.values():
            if p["state"] == "running":
                r = subprocess.run(["ps", "-o", "stat=", "-p", str(p["pid"])],
                                   capture_output=True, text=True).stdout.strip()
                if not r:
                    p["state"] = "gone"
                elif r.startswith("Z"):
                    p["state"] = "zombie"
        groups = [{"seq": s, "line": cmds[s],
                   "procs": [p for p in procs.values() if p["seq"] == s]} for s in sorted(cmds)]
        return {"shell": g.p.pid if shell is None else shell,
                "alive": g.p.poll() is None, "commands": groups, "history": g.history}


S = None


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _ok_host(self):
        if self.headers.get("Host") not in ALLOWED_HOSTS:
            self._send(403, {"error": "Host толгой зөвшөөрөгдөөгүй"})
            return False
        return True

    def do_GET(self):
        if not self._ok_host():
            return
        if self.path == "/api/tree":
            self._send(200, S.tree())
        elif self.path in ("/", "/index.html"):
            with open(os.path.join(ROOT, "ui", "index.html"), "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self._ok_host():
            return
        origin = self.headers.get("Origin")
        if origin is not None and origin not in ALLOWED_ORIGINS:
            self._send(403, {"error": "Өөр сайтаас ирсэн хүсэлтийг татгалзсан"})
            return
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            self._send(415, {"error": "Content-Type нь application/json байх ёстой"})
            return
        n = int(self.headers.get("Content-Length") or 0)
        if n > 64 * 1024:
            self._send(413, {"error": "Хүсэлт хэт том байна"})
            return
        try:
            data = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            self._send(400, {"error": "JSON буруу байна"})
            return
        if self.path == "/api/run":
            cmd = data.get("cmd")
            if not isinstance(cmd, str) or len(cmd.encode("utf-8")) > 1000:
                self._send(400, {"error": "cmd нь 1000 байтаас богино текст байх ёстой"})
                return
            self._send(200, S.run(cmd))
        elif self.path == "/api/reset":
            S.reset()
            self._send(200, {"ok": True})
        else:
            self._send(404, {"error": "not found"})


if __name__ == "__main__":
    if not os.path.exists(OSH):
        raise SystemExit("osh бүтээгдээгүй байна. Эхлээд `make` ажиллуулна уу.")
    S = Session()
    print(f"Open http://127.0.0.1:{PORT}  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
