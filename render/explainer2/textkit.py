"""textkit.py - all text for the explainer renderer (one family: Poppins; Amiri only for Arabic script).

Two kinds of text:
  * art text (speech bubbles, phone chat) -> cairo surfaces that move with the camera
  * overlay text (title zone, captions, source, hadith reveal) -> numpy RGBA blits, never scaled
"""
import os, re, math
import numpy as np
import cairo
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = next((d for d in (os.path.join(HERE, "fonts"), os.path.join(HERE, "..", "..", "fonts"))
                 if os.path.exists(os.path.join(d, "Poppins-Bold.ttf"))), os.path.join(HERE, "fonts"))
_F = {}
_S = {}


def font(name, size):
    k = (name, size)
    if k not in _F:
        _F[k] = ImageFont.truetype(os.path.join(FONT_DIR, name), size)
    return _F[k]


def is_arabic(s):
    return any("؀" <= ch <= "ۿ" or "ﭐ" <= ch <= "﷿" or "ﹰ" <= ch <= "﻿" for ch in s)


# ------------------------------------------------------------------ PIL -> cairo
def pil_to_surface(img):
    a = np.asarray(img.convert("RGBA"), dtype=np.float32)
    al = a[..., 3:4] / 255.0
    pm = np.concatenate([a[..., 2:3] * al, a[..., 1:2] * al, a[..., 0:1] * al, a[..., 3:4]], axis=2).astype(np.uint8)
    h, w = pm.shape[:2]
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    stride = s.get_stride()
    buf = np.ndarray((h, stride // 4, 4), np.uint8, s.get_data())
    buf[:, :w] = pm
    s.mark_dirty()
    return s


def _font_for(ch_text, fname, size):
    if is_arabic(ch_text) and not fname.startswith("amiri"):
        return font("amiri-ar.ttf", int(size * (1.5 if ch_text.strip() == "ﷺ" else 1.15)))
    return font(fname, size)


def render_text(text, fname, size, color, shadow=False, spacing=0):
    """All text shares the baseline of the requested (Poppins) font, so mixed runs line up."""
    base = font(fname, size)
    asc, desc = base.getmetrics()
    col = tuple(color) + ((255,) if len(color) == 3 else ())
    # split into runs (latin / arabic) - spaced labels go char by char
    if spacing:
        runs = [(c, _font_for(c, fname, size)) for c in text]
    elif fname.startswith("amiri"):
        runs = [(text, base)]
    else:
        runs, cur = [], ""
        for ch in text:
            if cur and is_arabic(ch) != is_arabic(cur[-1]):
                runs.append((cur, _font_for(cur, fname, size)))
                cur = ""
            cur += ch
        if cur:
            runs.append((cur, _font_for(cur, fname, size)))
    def kw(t_):
        return dict(direction="rtl", language="ar") if is_arabic(t_) and len(t_.strip()) > 1 else {}
    widths = [f.getlength(t_, **kw(t_)) for t_, f in runs]
    w = int(sum(widths) + spacing * max(0, len(runs) - 1)) + 10
    top_pad = int(size * 0.45)
    h = asc + desc + top_pad + 8
    img = Image.new("RGBA", (w + 6, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x, by = 3, top_pad + asc
    for (t_, f), wd in zip(runs, widths):
        if shadow:
            d.text((x + 1, by + 3), t_, font=f, fill=(0, 0, 0, 150), anchor="ls", **kw(t_))
        d.text((x, by), t_, font=f, fill=col, anchor="ls", **kw(t_))
        x += wd + spacing
    img.info["top_pad"] = top_pad
    return img


def text_surface(text, fname, size, color):
    k = ("s", text, fname, size, tuple(color))
    if k not in _S:
        img = render_text(text, fname, size, color)
        _S[k] = (pil_to_surface(img), img.size[0], img.size[1])
    return _S[k]


def paint_text(cr, text, fname, size, color, x, y, alpha=1.0):
    s, w, h = text_surface(text, fname, size, color)
    cr.set_source_surface(s, x, y)
    cr.paint_with_alpha(alpha)
    return w, h


def wrap(words, f, maxw):
    lines, cur = [], []
    for w in words:
        test = " ".join(cur + [w])
        if cur and f.getlength(test) > maxw:
            lines.append(cur)
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(cur)
    return lines


def chat_bubble(cr, x, y, maxw, who, msg, col, incoming=True, alpha=1.0, rise=0.0, right=None):
    """cairo chat bubble; returns the y below it."""
    f = font("Poppins-Regular.ttf", 27)
    lines = [" ".join(l) for l in wrap(msg.split(), f, maxw - 40)]
    lh = 37
    tw = max(f.getlength(l) for l in lines)
    if who:
        tw = max(tw, font("Poppins-Medium.ttf", 20).getlength(who))
    bw = tw + 36
    bh = len(lines) * lh + 24 + (26 if who else 0)
    bx = x if incoming else (right - bw)
    by = y + rise
    cr.push_group()
    cr.set_source_rgba(*((0.165, 0.18, 0.215) if incoming else col[:3]), 1)
    from art import rrect
    rrect(cr, bx, by, bw, bh, 20)
    cr.fill()
    ty = by + 10
    if who:
        paint_text(cr, who, "Poppins-Medium.ttf", 20, tuple(int(c * 255) for c in col[:3]), bx + 16, ty - 6)
        ty += 26
    for l in lines:
        paint_text(cr, l, "Poppins-Regular.ttf", 27, (236, 236, 236), bx + 16, ty - 8)
        ty += lh
    cr.pop_group_to_source()
    cr.paint_with_alpha(alpha)
    return y + bh + 12


# ------------------------------------------------------------------ overlay (numpy) text
GOLD = (240, 196, 108)
CREAM = (246, 240, 228)


def blit(frame, img, x, y, alpha=1.0):
    """frame: HxWx3 float32 (RGB). img: HxWx4 float32 RGBA (0-255)."""
    if alpha <= 0.003:
        return
    h, w = img.shape[:2]
    H_, W_ = frame.shape[:2]
    x, y = int(round(x)), int(round(y))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W_, x + w), min(H_, y + h)
    if x0 >= x1 or y0 >= y1:
        return
    sub = img[y0 - y:y1 - y, x0 - x:x1 - x]
    a = sub[..., 3:4] / 255.0 * alpha
    frame[y0:y1, x0:x1] = frame[y0:y1, x0:x1] * (1 - a) + sub[..., :3] * a


def rect(frame, x, y, w, h, color, alpha):
    x0, y0 = int(max(0, x)), int(max(0, y))
    x1, y1 = int(min(frame.shape[1], x + w)), int(min(frame.shape[0], y + h))
    if x1 > x0 and y1 > y0 and alpha > 0:
        frame[y0:y1, x0:x1] = frame[y0:y1, x0:x1] * (1 - alpha) + np.array(color, np.float32) * alpha


_W = {}


def word_img(text, fname, size, color, shadow=True):
    k = (text, fname, size, tuple(color), shadow)
    if k not in _W:
        _W[k] = np.asarray(render_text(text, fname, size, color, shadow=shadow), dtype=np.float32)
    return _W[k]


def tokens(s):
    """'Keep it *covered*.' -> [('Keep',F),('it',F),('covered.',T)] ; multi-word *a b* supported."""
    out, kw = [], False
    for w in s.split():
        st = w.startswith("*")
        en = w.rstrip(".,:;!?\"'”").endswith("*")
        flag = kw or st
        out.append((w.replace("*", ""), flag))
        if st and not en:
            kw = True
        if en:
            kw = False
    return out


def _wordw(t_, fname, size):
    return word_img(t_, fname, size, (255, 255, 255)).shape[1] - 13


def _rows(ws, sp, maxw):
    rows, cur, cw = [], [], 0
    for item in ws:
        w = item[2]
        if cur and cw + sp + w > maxw:
            rows.append((cur, cw))
            cur, cw = [], 0
        cw = cw + (sp if cur else 0) + w
        cur.append(item)
    if cur:
        rows.append((cur, cw))
    return rows


def layout(toks, fname, size, maxw, cx, top, lh):
    f = font(fname, size)
    sp = f.getlength(" ")
    ws = [(t_, k, _wordw(t_, fname, size)) for t_, k in toks]
    rows = _rows(ws, sp, maxw)
    n = len(rows)
    if n > 1:  # balance: shrink the box while the row count stays the same
        m = maxw
        while m > 300:
            r2 = _rows(ws, sp, m - 20)
            if len(r2) != n:
                break
            m -= 20
            rows = r2
    out = []
    for r, (row, rw) in enumerate(rows):
        x = cx - rw / 2
        for t_, k, w in row:
            out.append(dict(text=t_, kw=k, x=x, y=top + r * lh, w=w, row=r))
            x += w + sp
    return out, len(rows)


class Overlay:
    """Fixed safe zones (1080x1920, YouTube Shorts UI covers below ~y=1480):
       TITLE  y 150-450 : label / title / arabic line
       SCENE  y 450-1140: art only (or the hadith reveal block)
       BOTTOM y 1160-1440: caption (2 rows) + source pill"""
    TITLE_LABEL_Y = 160
    TITLE_Y = 206
    CAP_TOP = 1168
    SRC_Y = 1372

    def __init__(self, accent=GOLD):
        self.acc = accent
        self.cache = {}

    # ---------------- title zone
    def title(self, frame, S, t):
        label, title, arabic = S.get("label"), S.get("title"), S.get("arabic")
        if not (label or title or arabic):
            return
        a = ease((t - 0.12) / 0.35) * (1 - ease((t - (S["dur"] - 0.3)) / 0.18))
        dy = 18 * (1 - ease((t - 0.12) / 0.35))
        y = self.TITLE_LABEL_Y
        if label:
            img = self._spaced(label)
            blit(frame, img, 540 - img.shape[1] / 2, y + dy, a)
            y += 50
        else:
            y = self.TITLE_Y - 10
        if title:
            size = S.get("title_size", 60)
            k = ("title", title, size)
            if k not in self.cache:
                lay, nrows = layout(tokens(title), "Poppins-Bold.ttf", size, 930, 540, 0, int(size * 1.28))
                self.cache[k] = (lay, nrows)
            lay, nrows = self.cache[k]
            for wd in lay:
                img = word_img(wd["text"], "Poppins-Bold.ttf", size, self.acc if wd["kw"] else CREAM)
                blit(frame, img, wd["x"] - 2, y + wd["y"] + dy, a)
                if wd["kw"]:
                    u = ease((t - 0.25) / 0.45)
                    asc = font("Poppins-Bold.ttf", size).getmetrics()[0]
                    rect(frame, wd["x"] + 2, y + wd["y"] + int(size * 0.45) + asc + 10 + dy, wd["w"] * u, 6, self.acc, a)
            y += nrows * int(size * 1.28) + 22
        if arabic:
            img = word_img(arabic, "amiri-ar.ttf", 52, CREAM)
            a2 = ease((t - 0.3) / 0.4) * (1 - ease((t - (S["dur"] - 0.3)) / 0.18))
            blit(frame, img, 540 - img.shape[1] / 2, y + (1 - a2) * 12, a2 * 0.95)

    def _spaced(self, label):
        k = ("label", label)
        if k not in self.cache:
            self.cache[k] = np.asarray(render_text(label.upper(), "Poppins-Medium.ttf", 33, self.acc, shadow=True, spacing=5),
                                       dtype=np.float32)
        return self.cache[k]

    # ---------------- captions (word by word)
    def caption(self, frame, line, t, t_end):
        size = 54
        k = ("cap", line["text"])
        if k not in self.cache:
            toks = tokens(line["text"])
            lay, nrows = layout(toks, "Poppins-Bold.ttf", size, 940, 540, 0, 72)
            if nrows > 2:
                size = 46
                lay, nrows = layout(toks, "Poppins-Bold.ttf", size, 960, 540, 0, 62)
            # word times: proportional to length inside the spoken line
            wts = [len(w["text"]) + 3 for w in lay]
            tot = sum(wts)
            acc = 0
            for w, x in zip(lay, wts):
                w["t"] = line["start"] + line["dur"] * acc / tot
                acc += x
            self.cache[k] = (lay, nrows, size)
        lay, nrows, size = self.cache[k]
        out = 1 - ease((t - (t_end - 0.12)) / 0.12)
        top = self.CAP_TOP + (0 if nrows == 2 else 36)
        for w in lay:
            u = (t - w["t"] + 0.06) / 0.16
            if u <= 0:
                continue
            a = ease(u) * out
            img = word_img(w["text"], "Poppins-Bold.ttf", size, self.acc if w["kw"] else CREAM)
            blit(frame, img, w["x"] - 2, top + w["y"] + 14 * (1 - ease_out(u)), a)

    # ---------------- source pill
    def source(self, frame, S, t):
        s = S.get("source")
        if not s:
            return
        a = ease((t - 0.3) / 0.4) * (1 - ease((t - (S["dur"] - 0.3)) / 0.18))
        img = self._src(s)
        w, h = img.shape[1], img.shape[0]
        x = 540 - w / 2
        rect(frame, x - 26, self.SRC_Y - 6, w + 52, h + 12, (14, 12, 18), 0.55 * a)
        rect(frame, x - 26, self.SRC_Y - 6, 4, h + 12, self.acc, 0.9 * a)
        blit(frame, img, x, self.SRC_Y, a)

    def _src(self, s):
        k = ("src", s)
        if k not in self.cache:
            self.cache[k] = np.asarray(render_text(s.upper(), "Poppins-Medium.ttf", 29, (236, 228, 212), spacing=2),
                                       dtype=np.float32)
        return self.cache[k]

    # ---------------- hadith / ayah reveal block (scene zone)
    def reveal(self, frame, S, t):
        rows = S.get("reveal")
        if not rows:
            return
        y = 440
        for r in rows:
            u = (t - r["t"]) / 0.45
            if u > 0:
                a = ease(u)
                img = word_img(r["ar"], "amiri-ar.ttf", 80, self.acc if r.get("kw") else CREAM)
                blit(frame, img, 540 - img.shape[1] / 2, y + 16 * (1 - ease_out(u)), a)
                g = self._gloss(r["en"])
                blit(frame, g, 540 - g.shape[1] / 2, y + 150, a * 0.95)
            y += 158

    def _gloss(self, s):
        k = ("gl", s)
        if k not in self.cache:
            self.cache[k] = np.asarray(render_text(s.upper(), "Poppins-Medium.ttf", 28, (220, 214, 200), shadow=True, spacing=3),
                                       dtype=np.float32)
        return self.cache[k]


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3
