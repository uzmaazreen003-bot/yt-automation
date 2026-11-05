"""YouTube thumbnail (1280x720): big hook text + the anime character."""
from PIL import Image, ImageDraw, ImageFilter

import char
from common import F, Theme, build_bg, mix, star_pts

PILL_TEXT = {"money": "MONEY TIP", "overthinking": "MIND TIP", "selfcare": "SELF-CARE", "mental_load": "HOME TIP"}


def make(text, palette, pillar, out_path, channel="Uzma Azreen Studio"):
    W, H = 1280, 720
    th = Theme(palette)
    im = build_bg(th, W, H).convert("RGBA")
    # big soft circle behind the character
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).ellipse((720, 40, 1280, 600), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(4))
    im.paste(Image.new("RGBA", (W, H), mix(th.accent, (255, 255, 255), 0.55) + (255,)), (0, 0), m)
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).ellipse((800, 120, 1200, 520), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(4))
    im.paste(Image.new("RGBA", (W, H), mix(th.accent2, (255, 255, 255), 0.45) + (255,)), (0, 0), m)

    variants, (cw, chh) = char.build(560, kinds=("closed",))
    ch = variants[("closed", False)]
    im.alpha_composite(ch, (W - cw - 10, 46))

    d = ImageDraw.Draw(im)
    # sparkles
    for x, y, r, c in [(690, 90, 26, th.accent), (730, 600, 18, th.accent3), (110, 640, 16, th.accent), (640, 330, 14, th.accent2)]:
        d.polygon(star_pts(x, y, r, 4, 0.25), fill=c)

    # pill
    label = PILL_TEXT.get(pillar, "TIPS")
    f = F("Bold", 30)
    tw = d.textlength(label, font=f)
    d.rounded_rectangle((50, 44, 50 + tw + 70, 100), radius=28, fill=th.accent)
    d.ellipse((68, 64, 84, 80), fill=th.white)
    d.text((98, 72), label, font=f, fill=th.white, anchor="lm")

    # hook text
    words = (text or "DEKHO YE").upper().split()
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if cur and len(t) > 12:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    lines = lines[:3]
    size = 150
    while size > 60:
        f = F("Bold", size)
        if max(d.textlength(l, font=f) for l in lines) <= 700 and size * 1.08 * len(lines) <= 470:
            break
        size -= 6
    f = F("Bold", size)
    lh = size * 1.08
    y = 130 + (470 - lh * len(lines)) / 2
    for i, ln in enumerate(lines):
        col = th.accent if i == len(lines) - 1 else th.ink
        x = 50
        d.text((x + 6, y + i * lh + 6), ln, font=f, fill=mix(th.ink, (255, 255, 255), 0.6), anchor="lt",
               stroke_width=10, stroke_fill=mix(th.ink, (255, 255, 255), 0.6))
        d.text((x, y + i * lh), ln, font=f, fill=col, anchor="lt", stroke_width=10, stroke_fill=(255, 255, 255))

    # channel strip
    fs = F("Bold", 28)
    sw = d.textlength(channel, font=fs)
    d.rounded_rectangle((50, 636, 50 + sw + 40, 686), radius=25, fill=th.card)
    d.text((70, 661), channel, font=fs, fill=th.ink, anchor="lm")
    im.convert("RGB").save(out_path, quality=92)
    return out_path
