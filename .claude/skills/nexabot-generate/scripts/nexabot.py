#!/usr/bin/env python3
"""NexaBot API client (nexabot.id): image, video, Seedance 2.5, music, TTS.

Key comes from env NEXABOT_KEY. GPT Image also needs env NEXABOT_TELEGRAM_ID;
without it, --gpt falls back to the Google image model (img mode).

  NEXABOT_KEY=... python3 nexabot.py credit
  NEXABOT_KEY=... NEXABOT_TELEGRAM_ID=... python3 nexabot.py img "<prompt>" --aspect 5 --gpt --out a.png
  NEXABOT_KEY=... python3 nexabot.py img "<prompt>" --aspect 1 --out a.jpg
  NEXABOT_KEY=... python3 nexabot.py i2v "<prompt>" --ratio 2 --resolution 1080 --media char.jpg --out shot.mp4
  NEXABOT_KEY=... python3 nexabot.py seedance "<prompt>" --duration 15 --ratio 2 --out s.mp4
  NEXABOT_KEY=... python3 nexabot.py music "<prompt>" --out m.wav
  NEXABOT_KEY=... python3 nexabot.py tts "<text>" --voice Kore --out vo.wav
"""
import json, os, sys, time, argparse, base64, mimetypes, urllib.request, urllib.error

BASE = "https://nexabot.id"
KEY = os.environ.get("NEXABOT_KEY", "").strip()
TELEGRAM_ID = os.environ.get("NEXABOT_TELEGRAM_ID", "").strip()

if not KEY or "PASTE" in KEY:
    sys.exit("NO_KEY: API key belum diisi. Isi API_KEY dalam SKILL.md atau bagi key dalam chat.")


def req(path, body=None, raw=False):
    h = {"x-api-key": KEY, "User-Agent": "nexabot-generate-skill"}
    data = None
    if body is not None:
        h["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    r = urllib.request.Request(BASE + path, data=data, headers=h, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(r, timeout=180) as resp:
            b = resp.read()
            return b if raw else json.loads(b)
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors="replace")[:300]
        hint = {401: "API key salah atau dah dibatalkan.",
                402: "Credit API tak cukup. Top up credit (plan Unlimited web tak cover API).",
                403: "Job ni bukan milik akaun ni.",
                404: "Job tak jumpa.",
                409: "Job masih diproses."}.get(e.code, "")
        sys.exit(f"HTTP {e.code}: {hint} {msg}")
    except urllib.error.URLError as e:
        sys.exit(f"NETWORK: tak dapat sambung ke nexabot.id ({e.reason}). "
                 "Benarkan akses network ke nexabot.id dalam setting Claude.")


def data_uri(p):
    mt = mimetypes.guess_type(p)[0] or "application/octet-stream"
    return f"data:{mt};base64," + base64.b64encode(open(p, "rb").read()).decode()


def ratio_val(r):
    return int(r) if r is not None and str(r).isdigit() else r


ap = argparse.ArgumentParser()
ap.add_argument("mode"); ap.add_argument("prompt", nargs="?", default="")
ap.add_argument("--aspect", type=int); ap.add_argument("--ratio")
ap.add_argument("--resolution", type=int); ap.add_argument("--voice")
ap.add_argument("--duration", type=int, default=15)
ap.add_argument("--gpt", action="store_true")
ap.add_argument("--media", nargs="*", default=[]); ap.add_argument("--out")
a = ap.parse_args()

if a.mode == "credit":
    print("balance", req("/api/v1/api/credit").get("credit"))
    sys.exit(0)
if not a.out:
    sys.exit("--out diperlukan")

t0 = time.time()
model = a.mode

if a.mode == "seedance":
    body = {"prompt": a.prompt, "duration": a.duration, "ratio": ratio_val(a.ratio) or 1}
    if a.media: body["media"] = [data_uri(a.media[0])]
    sub = req("/api/v1/seedance", body)
    if not sub.get("ok"): sys.exit(f"submit failed: {sub}")
    jid = sub["job_id"]
    print("seedance job", jid, "cost", sub.get("credit_cost"), "queue", sub.get("queue_position"),
          "eta", sub.get("eta_seconds"), flush=True)
    while True:
        r = req(f"/api/v1/seedance/{jid}")
        job = r.get("job", r)
        st = str(job.get("status", "")).lower()
        if st in ("done", "completed", "success", "failed", "error"): break
        if time.time() - t0 > 3600: sys.exit("timeout")
        time.sleep(10)
    if st in ("failed", "error"):
        sys.exit(f"failed: {job.get('error')} (credit dipulangkan)")
    open(a.out, "wb").write(req(f"/api/v1/seedance/{jid}/download", raw=True))
    model = "Seedance 2.5"
elif a.gpt and TELEGRAM_ID:
    sub = req("/api/v1/gpt-image", {"prompt": a.prompt, "aspect": a.aspect or 1,
              "references": [data_uri(p) for p in a.media], "telegram_id": TELEGRAM_ID})
    if not sub.get("ok"): sys.exit(f"submit failed: {sub}")
    jid = sub["id"]
    print("gpt job", jid, "cost", sub.get("cost"), flush=True)
    while True:
        job = req(f"/api/v1/gpt-image/{jid}")["job"]
        if job["status"] in ("completed", "done", "failed", "error"): break
        if time.time() - t0 > 900: sys.exit("timeout")
        time.sleep(3)
    if job["status"] in ("failed", "error") or not job.get("images"):
        sys.exit(f"GPT_FAILED: {job.get('error')} (cuba semula tanpa --gpt)")
    open(a.out, "wb").write(req(job["images"][0]["url"], raw=True))
    model = "GPT Image"
else:
    if a.gpt and not TELEGRAM_ID:
        print("note: TELEGRAM_ID kosong, guna model Google (img mode)", flush=True)
    body = {"mode": a.mode}
    if a.prompt: body["prompt"] = a.prompt
    for k in ("aspect", "resolution", "voice"):
        if getattr(a, k) is not None: body[k] = getattr(a, k)
    if a.ratio is not None: body["ratio"] = ratio_val(a.ratio)
    if a.media: body["media"] = [data_uri(p) for p in a.media]
    sub = req("/api/v1/api", body)
    jid = sub["job_id"]
    print("job", jid, "cost", sub.get("credit_cost"), "unlimited", sub.get("unlimited", False), flush=True)
    while True:
        job = req(f"/api/v1/jobs/{jid}")["job"]
        if job["status"] in ("done", "failed"): break
        if time.time() - t0 > 900: sys.exit("timeout")
        time.sleep(3)
    if job["status"] == "failed":
        sys.exit(f"failed: {job.get('error')} (credit dipulangkan)")
    open(a.out, "wb").write(req(f"/api/v1/jobs/{jid}/download", raw=True))
    if a.mode == "img": model = "Google image"

bal = req("/api/v1/api/credit")
print("saved", a.out, "| model", model, "| balance", bal.get("credit"))
