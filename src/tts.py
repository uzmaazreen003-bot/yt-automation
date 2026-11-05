"""edge-tts Hindi narration, one mp3 per scene, with word timing when the service provides it."""
import asyncio
import os
import subprocess
import time

import edge_tts


async def _run(text, voice, rate, out):
    try:
        com = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    except TypeError:
        com = edge_tts.Communicate(text, voice, rate=rate)
    events = []
    with open(out, "wb") as f:
        async for ch in com.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                off, dur = ch["offset"] / 1e7, ch["duration"] / 1e7
                events.append((ch.get("text", ""), off, off + dur))
    return events


def synth(text, voice, rate, out, tries=5):
    last = None
    for i in range(tries):
        try:
            ev = asyncio.run(_run(text, voice, rate, out))
            if os.path.exists(out) and os.path.getsize(out) > 2000:
                return ev
            last = "empty audio"
        except Exception as e:  # noqa: BLE001
            last = e
        print(f"  tts retry {i + 1}: {last}")
        time.sleep(3 * (i + 1))
    raise RuntimeError(f"TTS failed: {last}")


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())
