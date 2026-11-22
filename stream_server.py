"""Lumora stream server - jalan di HP (Pydroid 3).
Hanya mengambil URL audio lewat yt-dlp. Vercel tidak dipakai untuk ini karena diblokir.
Jalankan: uvicorn stream_server:app --host 0.0.0.0 --port 8000
Lalu expose ke internet (mis. cloudflared tunnel --url http://localhost:8000) dan isi LUMORA_STREAM di config.js.
"""
import re, time
from fastapi import FastAPI
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_SC = {}  # vid -> (expire_ts, url)

def _resolve_audio(vid):
    now = time.time()
    hit = _SC.get(vid)
    if hit and hit[0] > now:
        return hit[1]
    import yt_dlp
    opts = {"format": "bestaudio[ext=m4a]/bestaudio/best", "quiet": True, "no_warnings": True,
            "noplaylist": True, "skip_download": True, "socket_timeout": 15}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
    fmt = info if info.get("url") else (info.get("requested_formats") or [info])[0]
    url = fmt.get("url")
    if not url:
        raise RuntimeError("no audio url")
    _SC[vid] = (now + 3600, url)
    return url

@app.get("/")
def root():
    return {"ok": True, "service": "lumora-stream"}

@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/stream/{vid}")
def stream(vid: str):
    """302 redirect ke URL audio; <audio src> langsung memakainya."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,20}", vid):
        return JSONResponse({"err": "vid tidak valid"}, 400)
    try:
        return RedirectResponse(_resolve_audio(vid), 302, headers={"Cache-Control": "no-store"})
    except Exception as e:
        return JSONResponse({"err": repr(e)[:200]}, 502)
