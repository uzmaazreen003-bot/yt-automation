"""Offline test: mock script (all 10 templates), silent fake narration, renders stills or a short clip."""
import json
import os
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

import render  # noqa: E402
import sfx  # noqa: E402
import timeline  # noqa: E402

CFG = json.load(open(os.path.join(ROOT, "config.json")))


def sc(en, takeaway, v, hi=None):
    en_t = en.split()
    return dict(en=en, hi=hi or en, en_tokens=en_t, hi_tokens=(hi or en).split(), takeaway=takeaway, v=v)


PRODUCT = CFG["products"]["first_salary"]
SCENES = [
    sc("Pehli salary aayi? Ruko, pehle ye teen kaam karo.", "Pehle plan, phir kharch",
       dict(type="title", heading="Pehli salary aayi? Pehle ye karo", sub="3 simple steps jo har ladki ko pata hone chahiye", icon="coin")),
    sc("Sabse pehle salary ko teen hisson mein baanto: pachaas percent zaroorat, tees percent shauk aur bees percent savings.",
       "50 / 30 / 20 rule",
       dict(type="split_bar", heading="50 / 30 / 20 rule", segments=[
           dict(label="Needs", pct=50, note="Rent, bills", cue="pachaas"), dict(label="Wants", pct=30, note="Shopping, outing", cue="tees"),
           dict(label="Savings", pct=20, note="Pehle alag", cue="bees")])),
    sc("Agar salary pachchees hazaar hai to savings ke liye paanch hazaar rupaye alag rakho.", "Savings pehle alag",
       dict(type="big_number", label="25,000 salary mein savings", value=5000, prefix="₹", sub="Har mahine, pehle din", icon="coin")),
    sc("Teen kadam: kharche likho, limit set karo aur savings auto transfer karo.", "3 kadam, bas",
       dict(type="steps", heading="3 simple kadam", items=[dict(text="Kharche likho", cue="kharche"), dict(text="Limit set karo", cue="limit"),
                                                      dict(text="Auto transfer lagao", cue="auto")])),
    sc("Galat tareeka hai mahine ke end mein bacha hua save karna, sahi tareeka hai pehle save karna.", "Pehle save karo",
       dict(type="compare", heading="Galat vs Sahi", left=dict(title="Galat", items=["End mein bacha hua save", "Bina budget ke kharch"]),
            right=dict(title="Sahi", items=["Pehle save, phir kharch", "Mahine ka budget"]))),
    sc("In cheezon par dhyan do: emergency fund, credit card ka limit aur subscriptions.", "Chhupe kharche dekho",
       dict(type="checklist", heading="Ye check karo", items=[dict(text="Emergency fund", cue="emergency"), dict(text="Credit card limit", cue="credit"),
                                                          dict(text="Subscriptions band karo", cue="subscriptions")])),
    sc("Dekho ek ladki ke mahine ke kharche kaise baante hain: kiraya, khana aur shopping.", "Kharche ka chart",
       dict(type="bars", heading="Mahine ke kharche (₹)", items=[dict(label="Kiraya", value=9000, prefix="₹", cue="kiraya"),
                                                                 dict(label="Khana", value=5000, prefix="₹", cue="khana"),
                                                                 dict(label="Shopping", value=3000, prefix="₹", cue="shopping")])),
    sc("Yaad rakho, paisa wahi bachta hai jiska tum pehle se plan banati ho.", "Plan banao, paisa bachao",
       dict(type="quote", text="Paisa wahi bachta hai jiska pehle se plan hota hai.", by="Uzma")),
    sc("Poora step by step workbook mere Payhip store pe hai, link description mein hai, zaroor dekhna.", "Workbook link neeche",
       dict(type="cta", product="first_salary", items=[dict(text="Spending samjho"), dict(text="Savings banao"), dict(text="Emergency fund")], _product=PRODUCT)),
]


def make_plan(fmt, palette):
    scenes = [dict(s) for s in SCENES]
    out = os.path.join(ROOT, "out", "mock_audio")
    os.makedirs(out, exist_ok=True)
    durs, evs = [], []
    for i, s in enumerate(scenes):
        d = len(s["en_tokens"]) * 0.42 + 0.3
        p = os.path.join(out, f"s{i}.wav")
        with wave.open(p, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sfx.SR)
            wf.writeframes(b"\x00\x00" * int(d * sfx.SR))
        s["audio"] = p
        durs.append(d)
        evs.append(None)
    plan = dict(format=fmt, palette=palette, pillar="money", scenes=scenes)
    voice, events = timeline.build(plan, durs, evs)
    return plan, voice, events


if __name__ == "__main__":
    fmt, palette, mode = sys.argv[1], sys.argv[2], sys.argv[3]
    plan, voice, events = make_plan(fmt, palette)
    print("total", round(plan["total"], 1), "scenes", [round(s["t0"], 1) for s in plan["scenes"]])
    if mode == "stills":
        r = render.Renderer(plan, CFG)
        for k, s in enumerate(plan["scenes"]):
            for frac in (0.55,):
                t = s["t0"] + s["len"] * frac
                r.frame(t).save(os.path.join(ROOT, "out", f"still_{fmt}_{k}.png"))
    else:
        wav = os.path.join(ROOT, "out", "mock.wav")
        sfx.mix_audio(voice, events, plan["total"], wav)
        render.render_video(plan, CFG, wav, os.path.join(ROOT, "out", f"mock_{fmt}.mp4"), max_seconds=float(sys.argv[4]) if len(sys.argv) > 4 else None)
