"""Orchestrator: pick topic -> script (Gemini) -> voice (edge-tts) -> render -> thumbnail -> upload (or dry-run)."""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import common  # noqa: E402
import render  # noqa: E402
import sfx  # noqa: E402
import timeline  # noqa: E402

CFG = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))
STATE_PATH = os.path.join(ROOT, "state.json")


def load_state():
    try:
        return json.load(open(STATE_PATH, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return dict(palette_i=0, used=dict(long=[], short=[]), log=[])


def save_state(st):
    json.dump(st, open(STATE_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def pick_topic(st, fmt):
    topics = json.load(open(os.path.join(ROOT, "topics.json"), encoding="utf-8"))
    used = st["used"].setdefault(fmt, [])
    left = [t for t in topics if t["topic"] not in used]
    if not left:
        used.clear()
        left = topics
    # rotate pillars: choose the pillar least recently used across both formats
    recent = [e.get("pillar") for e in st.get("log", [])][-4:]
    left.sort(key=lambda t: (recent[::-1].index(t["pillar"]) if t["pillar"] in recent else 99), reverse=True)
    return left[0]


def fmt_ts(sec):
    sec = int(sec)
    return f"{sec // 60}:{sec % 60:02d}"


def build_description(plan, fmt, product):
    parts = []
    if plan.get("intro"):
        parts.append(plan["intro"])
    parts.append(f"📘 {product['title']} ({product['price']}): {product['tagline']}\n👉 {product['link']}")
    parts.append(f"🛍️ Mera poora store: {CFG['store_url']}")
    if fmt == "long" and plan.get("chapters"):
        ch = [f"{fmt_ts(plan['scenes'][c['scene']]['t0'])} {c['title']}" for c in plan["chapters"] if c["scene"] < len(plan["scenes"])]
        if len(ch) >= 3:
            parts.append("⏱️ Chapters:\n" + "\n".join(ch))
    parts.append("Subscribe karo 💛 Mind, Money aur Self-care ki simple Hinglish tips ke liye.")
    parts.append("Disclaimer: Ye video sirf educational jaankari ke liye hai, financial ya medical salah nahi. "
                 "Is video mein AI-assisted voice aur visuals ka use hua hai.")
    tags = plan.get("tags") or []
    hs = " ".join("#" + t.replace(" ", "") for t in (tags[:3] or ["selfcare"]))
    if fmt == "short":
        hs = "#Shorts " + hs
    parts.append(hs)
    return "\n\n".join(parts)


def run(fmt, mock=False, outdir=None):
    st = load_state()
    outdir = outdir or os.path.join(ROOT, "out")
    os.makedirs(outdir, exist_ok=True)
    audio_dir = os.path.join(outdir, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    palette = common.PALETTE_ORDER[st.get("palette_i", 0) % len(common.PALETTE_ORDER)]

    if mock:
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import mock_test
        plan, voice, events = mock_test.make_plan(fmt, palette)
        plan.update(title="Mock video", thumb_text="PEHLI SALARY", intro="", tags=["money", "salary"], chapters=[])
        topic = dict(pillar="money", topic="mock")
    else:
        import llm
        import tts
        topic = pick_topic(st, fmt)
        print(f"[{fmt}] topic: {topic['topic']} ({topic['pillar']}) palette={palette}")
        product_key = CFG["pillar_product"][topic["pillar"]]
        plan = llm.make_long(topic, CFG, product_key) if fmt == "long" else llm.make_short(topic, CFG, product_key)
        plan.update(format=fmt, palette=palette, pillar=topic["pillar"])
        print(f"  script ready: {len(plan['scenes'])} scenes, title: {plan['title']}")
        durs, evs = [], []
        for i, sc in enumerate(plan["scenes"]):
            p = os.path.join(audio_dir, f"s{i:03d}.mp3")
            evs.append(tts.synth(sc["hi"], CFG["voice"], CFG.get("voice_rate", "+0%"), p))
            sc["audio"] = p
            durs.append(tts.duration(p))
            time.sleep(0.3)
        voice, events = timeline.build(plan, durs, evs)
    product = CFG["products"][CFG["pillar_product"][topic["pillar"]]]
    print(f"  total length: {plan['total']:.0f}s")

    wav = os.path.join(outdir, "mix.wav")
    sfx.mix_audio(voice, events, plan["total"], wav)
    video = os.path.join(outdir, f"{fmt}.mp4")
    render.render_video(plan, CFG, wav, video)

    thumb = None
    if fmt == "long":
        import thumb as th
        thumb = th.make(plan.get("thumb_text") or "DEKHO YE", palette, topic["pillar"], os.path.join(outdir, "thumb.png"))

    title = plan["title"]
    if fmt == "short" and "#shorts" not in title.lower() and len(title) < 90:
        title += " #Shorts"
    desc = build_description(plan, fmt, product)
    comment = (f"📘 {product['title']} ({product['price']}) yahan se lo: {product['link']}\n"
               "Aapka sabse bada sawal kya hai? Comment mein likho, main zaroor jawab dungi 💛") if CFG.get("post_first_comment") else None
    meta = dict(title=title, description=desc, tags=plan.get("tags", []), format=fmt, topic=topic, palette=palette,
                seconds=round(plan["total"]), comment=comment)
    json.dump(meta, open(os.path.join(outdir, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(plan, open(os.path.join(outdir, "plan.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)

    uploaded = None
    enable = os.environ.get("ENABLE_UPLOAD", "false").lower() == "true"
    if mock:
        print("mock: no upload")
    elif not enable:
        print("DRY RUN: upload skipped (ENABLE_UPLOAD != true)")
    elif fmt == "long" and plan["total"] < CFG.get("long_min_seconds", 380) - 20:
        print(f"Video too short for a long ({plan['total']:.0f}s), upload skipped")
    else:
        import upload
        uploaded = upload.upload(video, title, desc, plan.get("tags", []), CFG, thumb, comment)
    if not mock:
        st["palette_i"] = st.get("palette_i", 0) + 1
        if enable or True:
            st["used"].setdefault(fmt, []).append(topic["topic"])
        st.setdefault("log", []).append(dict(date=time.strftime("%Y-%m-%d %H:%M"), format=fmt, topic=topic["topic"],
                                             pillar=topic["pillar"], title=title, video_id=uploaded))
        st["log"] = st["log"][-60:]
        save_state(st)
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", choices=["short", "long"], required=True)
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    run(a.format, a.mock, a.out)
