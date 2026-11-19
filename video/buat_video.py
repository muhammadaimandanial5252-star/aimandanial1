#!/usr/bin/env python3
"""Penjana video iklan menegak (9:16) untuk kedai pakaian.

Ubah bahagian KONFIGURASI di bawah, kemudian jalankan:
    python3 video/buat_video.py
Keperluan: Python 3, Pillow, numpy, ffmpeg.
"""
import math
import os
import random
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ======================= KONFIGURASI (ubah di sini) =======================
NAMA_KEDAI = "BUTIK SERI AYU"
SLOGAN = "Anggun setiap hari"
TAJUK_KOLEKSI = "KOLEKSI TERBARU"
HARGA = "Dari RM89"
DISKAUN = "30%"
TEKS_DISKAUN = "DISKAUN"
TEMPOH = "1 - 31 Disember sahaja"
KELEBIHAN = ["Kain premium & selesa", "Saiz XS hingga 3XL", "Pos ke seluruh Malaysia"]
AJAKAN = "BELI SEKARANG"
WHATSAPP = "WhatsApp 01X-XXX XXXX"
MEDIA_SOSIAL = "@butikseriayu"
FAIL_OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "iklan_butik.mp4")
# ==========================================================================

W, H, FPS = 1080, 1920, 30
DURASI = 16.0
N = int(DURASI * FPS)

PLUM = (46, 16, 44)
PLUM2 = (92, 30, 78)
EMAS = (226, 186, 110)
KRIM = (250, 240, 228)
MERAH = (214, 54, 88)
WARNA_BAJU = [(214, 84, 118), (64, 132, 150), (232, 170, 70)]

FONT_DIR = "/usr/share/fonts/truetype"
SERIF_B = f"{FONT_DIR}/dejavu/DejaVuSerif-Bold.ttf"
SANS_B = f"{FONT_DIR}/dejavu/DejaVuSans-Bold.ttf"
SANS = f"{FONT_DIR}/dejavu/DejaVuSans.ttf"
_fc = {}


def font(path, size):
    key = (path, int(size))
    if key not in _fc:
        _fc[key] = ImageFont.truetype(path, max(1, int(size)))
    return _fc[key]


# ---------- easing ----------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(t, start, dur):
    return clamp((t - start) / dur)


def ease_out(x):
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    return 3 * x * x - 2 * x * x * x


def back_out(x, s=1.9):
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


# ---------- latar ----------
def buat_latar():
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(0, 1, W)[None, :]
    r = np.sqrt((x - 0.5) ** 2 + ((y - 0.38) * 0.6) ** 2)
    m = clamp_arr(1 - r * 1.6)
    base = np.array(PLUM, float)
    glow = np.array(PLUM2, float)
    img = base[None, None, :] * (1 - m[..., None]) + glow[None, None, :] * m[..., None]
    return Image.fromarray(img.astype(np.uint8), "RGB")


def clamp_arr(a):
    return np.clip(a, 0, 1)


LATAR = buat_latar()
rng = random.Random(7)
KILAUAN = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(2, 6), rng.uniform(0, 6.28), rng.uniform(20, 60))
           for _ in range(70)]


def lukis_kilauan(d, t, alpha=1.0):
    for x, y, s, ph, sp in KILAUAN:
        yy = (y - t * sp) % H
        a = (0.5 + 0.5 * math.sin(t * 2.2 + ph)) * alpha
        if a < 0.05:
            continue
        c = tuple(int(PLUM[i] + (EMAS[i] - PLUM[i]) * a) for i in range(3))
        r = s * (0.6 + 0.4 * a)
        d.line([(x - r * 2, yy), (x + r * 2, yy)], fill=c, width=2)
        d.line([(x, yy - r * 2), (x, yy + r * 2)], fill=c, width=2)


# ---------- utiliti teks ----------
def teks_tengah(img, teks, y, fnt, warna, alpha=1.0, jarak=0, dx=0):
    """Lukis teks di tengah dengan ketelusan dan jarak huruf."""
    if alpha <= 0:
        return
    lapisan = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lapisan)
    lebar = sum(d.textlength(c, font=fnt) for c in teks) + jarak * (len(teks) - 1)
    x = (W - lebar) / 2 + dx
    for c in teks:
        d.text((x, y), c, font=fnt, fill=warna + (int(255 * alpha),), anchor="ls")
        x += d.textlength(c, font=fnt) + jarak
    img.alpha_composite(lapisan)


def bayang(img, kotak, radius, kabur=30, alpha=120):
    s = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(s).rounded_rectangle(kotak, radius, fill=(0, 0, 0, alpha))
    img.alpha_composite(s.filter(ImageFilter.GaussianBlur(kabur)))


# ---------- baju ----------
def lukis_baju(d, cx, top, skala, warna, corak):
    """Siluet baju kurung/dress ringkas pada penyangkut."""
    s = skala
    gelap = tuple(int(c * 0.72) for c in warna)
    # penyangkut
    d.arc([cx - 18 * s, top - 40 * s, cx + 18 * s, top - 4 * s], 180, 360 + 60, fill=EMAS, width=int(6 * s))
    d.line([(cx, top), (cx - 110 * s, top + 50 * s)], fill=EMAS, width=int(7 * s))
    d.line([(cx, top), (cx + 110 * s, top + 50 * s)], fill=EMAS, width=int(7 * s))
    d.line([(cx - 110 * s, top + 50 * s), (cx + 110 * s, top + 50 * s)], fill=EMAS, width=int(7 * s))
    # badan
    badan = [
        (cx - 40 * s, top + 30 * s), (cx + 40 * s, top + 30 * s),
        (cx + 105 * s, top + 60 * s), (cx + 170 * s, top + 230 * s),  # bahu & lengan kanan
        (cx + 130 * s, top + 250 * s), (cx + 85 * s, top + 140 * s),
        (cx + 75 * s, top + 220 * s), (cx + 150 * s, top + 560 * s),  # kain kanan
        (cx - 150 * s, top + 560 * s), (cx - 75 * s, top + 220 * s),
        (cx - 85 * s, top + 140 * s), (cx - 130 * s, top + 250 * s),
        (cx - 170 * s, top + 230 * s), (cx - 105 * s, top + 60 * s),
    ]
    d.polygon(badan, fill=warna)
    # leher
    d.chord([cx - 40 * s, top + 5 * s, cx + 40 * s, top + 75 * s], 0, 180, fill=gelap)
    # tali pinggang
    d.polygon([(cx - 77 * s, top + 205 * s), (cx + 77 * s, top + 205 * s),
               (cx + 80 * s, top + 232 * s), (cx - 80 * s, top + 232 * s)], fill=EMAS)
    # corak
    for i in range(corak):
        yy = top + (290 + i * 80) * s
        lebar = 78 + (yy - top - 230 * s) / s * 0.23
        for k in range(-3, 4):
            x = cx + k * lebar * s / 3.3
            d.ellipse([x - 9 * s, yy - 9 * s, x + 9 * s, yy + 9 * s], fill=KRIM)
    # garis bawah
    d.line([(cx - 150 * s, top + 545 * s), (cx + 150 * s, top + 545 * s)], fill=gelap, width=int(10 * s))


# ---------- babak ----------
def babak_jenama(img, d, t):
    # garis emas melukis dari tengah
    p = ease_out(prog(t, 0.2, 0.9))
    y1, y2 = 820, 1100
    d.line([(W / 2 - 330 * p, y1), (W / 2 + 330 * p, y1)], fill=EMAS, width=4)
    d.line([(W / 2 - 330 * p, y2), (W / 2 + 330 * p, y2)], fill=EMAS, width=4)
    # bunga kecil
    pb = back_out(prog(t, 0.5, 0.6))
    if pb > 0:
        r = 34 * pb
        for k in range(6):
            a = k * math.pi / 3 + t
            x, y = W / 2 + math.cos(a) * r * 0.9, 700 + math.sin(a) * r * 0.9
            d.ellipse([x - r * 0.55, y - r * 0.55, x + r * 0.55, y + r * 0.55], fill=EMAS)
        d.ellipse([W / 2 - r * 0.5, 700 - r * 0.5, W / 2 + r * 0.5, 700 + r * 0.5], fill=PLUM)
    # nama: setiap perkataan muncul
    pn = ease_out(prog(t, 0.6, 0.9))
    kata = NAMA_KEDAI.split(" ", 1)
    teks_tengah(img, kata[0], 945 + 40 * (1 - pn), font(SANS_B, 58), EMAS, pn, jarak=22)
    pn2 = ease_out(prog(t, 0.85, 0.9))
    teks_tengah(img, kata[1] if len(kata) > 1 else "", 1060 + 40 * (1 - pn2), font(SERIF_B, 118), KRIM, pn2, jarak=6)
    ps = ease_out(prog(t, 1.5, 0.8))
    teks_tengah(img, SLOGAN, 1190, font(SANS, 46), KRIM, ps, jarak=4)


def babak_koleksi(img, d, t):
    pj = ease_out(prog(t, 0.0, 0.6))
    teks_tengah(img, TAJUK_KOLEKSI, 330 - 30 * (1 - pj), font(SANS_B, 72), EMAS, pj, jarak=10)
    d.line([(W / 2 - 150 * pj, 375), (W / 2 + 150 * pj, 375)], fill=KRIM, width=3)
    pos = [(W / 2 - 335, 0.8), (W / 2, 1.02), (W / 2 + 335, 0.8)]
    susunan = [0, 2, 1]
    for n, i in enumerate(susunan):
        cx, s = pos[i]
        p = back_out(prog(t, 0.25 + n * 0.22, 0.75), 1.4)
        if p <= 0:
            continue
        hayun = math.sin(t * 2.4 + i) * 4 * (1 - prog(t, 1.5, 1.5))
        top = (560 if i == 1 else 660) + (1 - p) * 1400
        lapisan = Image.new("RGBA", img.size, (0, 0, 0, 0))
        lukis_baju(ImageDraw.Draw(lapisan), cx + hayun, top, s, WARNA_BAJU[i], 3)
        img.alpha_composite(lapisan)
    # tanda harga
    ph = back_out(prog(t, 1.4, 0.6))
    if ph > 0:
        lw, lh = 520 * ph, 120 * ph
        kotak = [W / 2 - lw / 2, 1420 - lh / 2, W / 2 + lw / 2, 1420 + lh / 2]
        bayang(img, kotak, 60 * ph)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle(kotak, 60 * ph, fill=KRIM)
        if ph > 0.6:
            d.text((W / 2, 1420), HARGA, font=font(SANS_B, 64 * ph), fill=PLUM, anchor="mm")


def babak_diskaun(img, d, t):
    # sinar berputar
    pr = ease_out(prog(t, 0.0, 0.5))
    sinar = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ds = ImageDraw.Draw(sinar)
    cx, cy = W / 2, 900
    for k in range(16):
        a0 = k * math.pi / 8 + t * 0.4
        a1 = a0 + math.pi / 16
        ds.polygon([(cx, cy), (cx + math.cos(a0) * 1500, cy + math.sin(a0) * 1500),
                    (cx + math.cos(a1) * 1500, cy + math.sin(a1) * 1500)], fill=EMAS + (int(28 * pr),))
    img.alpha_composite(sinar)
    d = ImageDraw.Draw(img)
    # lencana bintang
    pb = back_out(prog(t, 0.1, 0.7), 2.2)
    if pb > 0:
        R, r = 380 * pb, 330 * pb
        titik = []
        for k in range(48):
            a = k * math.pi / 24 - t * 0.3
            rr = R if k % 2 == 0 else r
            titik.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
        lap = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(lap).polygon(titik, fill=(0, 0, 0, 110))
        img.alpha_composite(lap.filter(ImageFilter.GaussianBlur(25)), (0, 20))
        d = ImageDraw.Draw(img)
        d.polygon(titik, fill=MERAH)
        d.ellipse([cx - 290 * pb, cy - 290 * pb, cx + 290 * pb, cy + 290 * pb], outline=KRIM, width=max(1, int(5 * pb)))
        denyut = 1 + 0.04 * math.sin(max(0, t - 0.8) * 9)
        if pb > 0.3:
            d.text((cx, cy - 120 * pb), TEKS_DISKAUN, font=font(SANS_B, 66 * pb), fill=KRIM, anchor="mm")
            d.text((cx, cy + 50 * pb), DISKAUN, font=font(SANS_B, 230 * pb * denyut), fill=KRIM, anchor="mm")
    pt = ease_out(prog(t, 0.8, 0.6))
    teks_tengah(img, TEMPOH, 1480 + 30 * (1 - pt), font(SANS_B, 54), KRIM, pt, jarak=2)
    pt2 = ease_out(prog(t, 1.1, 0.6))
    teks_tengah(img, "SEMUA KOLEKSI", 1580 + 30 * (1 - pt2), font(SANS, 44), EMAS, pt2, jarak=10)


def babak_kelebihan(img, d, t):
    pj = ease_out(prog(t, 0.0, 0.5))
    teks_tengah(img, "KENAPA PILIH KAMI?", 520 - 30 * (1 - pj), font(SERIF_B, 70), EMAS, pj, jarak=3)
    for i, item in enumerate(KELEBIHAN):
        p = ease_out(prog(t, 0.35 + i * 0.35, 0.6))
        if p <= 0:
            continue
        y = 760 + i * 230
        dx = (1 - p) * -500
        kotak = [120 + dx, y - 85, W - 120 + dx, y + 85]
        lap = Image.new("RGBA", img.size, (0, 0, 0, 0))
        dl = ImageDraw.Draw(lap)
        dl.rounded_rectangle(kotak, 40, fill=KRIM + (int(240 * p),))
        # bulatan tanda
        bx, by = 220 + dx, y
        dl.ellipse([bx - 52, by - 52, bx + 52, by + 52], fill=EMAS + (int(255 * p),))
        pc = ease_out(prog(t, 0.6 + i * 0.35, 0.4))
        if pc > 0:
            a = (bx - 24, by + 2)
            b = (bx - 6, by + 22)
            c = (bx + 28, by - 20)
            if pc < 0.4:
                q = pc / 0.4
                dl.line([a, (a[0] + (b[0] - a[0]) * q, a[1] + (b[1] - a[1]) * q)], fill=PLUM, width=12)
            else:
                q = (pc - 0.4) / 0.6
                dl.line([a, b, (b[0] + (c[0] - b[0]) * q, b[1] + (c[1] - b[1]) * q)], fill=PLUM, width=12, joint="curve")
        dl.text((310 + dx, y), item, font=font(SANS_B, 46), fill=PLUM + (int(255 * p),), anchor="lm")
        img.alpha_composite(lap)


def babak_ajakan(img, d, t):
    pn = ease_out(prog(t, 0.0, 0.6))
    teks_tengah(img, NAMA_KEDAI, 560 - 30 * (1 - pn), font(SERIF_B, 76), EMAS, pn, jarak=4)
    d = ImageDraw.Draw(img)
    d.line([(W / 2 - 200 * pn, 610), (W / 2 + 200 * pn, 610)], fill=EMAS, width=3)
    # butang
    pb = back_out(prog(t, 0.3, 0.7))
    if pb > 0:
        denyut = 1 + 0.035 * math.sin(max(0, t - 1.0) * 6.5)
        bw, bh = 760 * pb * denyut, 170 * pb * denyut
        kotak = [W / 2 - bw / 2, 860 - bh / 2, W / 2 + bw / 2, 860 + bh / 2]
        bayang(img, kotak, bh / 2, alpha=140)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle(kotak, bh / 2, fill=MERAH)
        # kilat menyapu butang
        if t > 1.0:
            sx = W / 2 - bw / 2 + ((t - 1.0) % 1.6) / 1.6 * (bw + 300) - 150
            kil = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(kil).polygon([(sx, kotak[1]), (sx + 60, kotak[1]), (sx - 10, kotak[3]), (sx - 70, kotak[3])],
                                        fill=(255, 255, 255, 70))
            topeng = Image.new("L", img.size, 0)
            ImageDraw.Draw(topeng).rounded_rectangle(kotak, bh / 2, fill=255)
            kil.putalpha(Image.fromarray(np.minimum(np.array(kil.getchannel("A")), np.array(topeng))))
            img.alpha_composite(kil)
            d = ImageDraw.Draw(img)
        if pb > 0.4:
            d.text((W / 2, 860), AJAKAN, font=font(SANS_B, 72 * pb * denyut), fill=KRIM, anchor="mm")
    for i, (teks, warna, sz) in enumerate([(WHATSAPP, KRIM, 56), (MEDIA_SOSIAL, EMAS, 52)]):
        p = ease_out(prog(t, 0.8 + i * 0.3, 0.6))
        teks_tengah(img, teks, 1130 + i * 110 + 30 * (1 - p), font(SANS_B, sz), warna, p, jarak=1)
    pf = ease_out(prog(t, 1.6, 0.6))
    teks_tengah(img, SLOGAN, 1560, font(SANS, 42), KRIM, pf * 0.8, jarak=6)


BABAK = [  # (fungsi, mula, tamat)
    (babak_jenama, 0.0, 3.0),
    (babak_koleksi, 3.0, 6.6),
    (babak_diskaun, 6.6, 9.8),
    (babak_kelebihan, 9.8, 12.8),
    (babak_ajakan, 12.8, DURASI),
]
PERALIHAN = 0.35


def bingkai(i):
    t = i / FPS
    img = LATAR.copy().convert("RGBA")
    d = ImageDraw.Draw(img)
    lukis_kilauan(d, t)
    for fn, a, b in BABAK:
        if a - PERALIHAN <= t < b + PERALIHAN:
            lap = Image.new("RGBA", img.size, (0, 0, 0, 0))
            fn(lap, ImageDraw.Draw(lap), t - a)
            # pudar masuk/keluar
            alpha = 1.0
            if t < a + PERALIHAN and a > 0:
                alpha = ease_in_out(prog(t, a - 0.0, PERALIHAN))
            if t > b - PERALIHAN and b < DURASI:
                alpha = min(alpha, 1 - ease_in_out(prog(t, b - PERALIHAN, PERALIHAN)))
            if t < a or (t >= b and b < DURASI):
                continue
            if alpha < 1:
                al = np.array(lap.getchannel("A"), dtype=np.float32) * alpha
                lap.putalpha(Image.fromarray(al.astype(np.uint8)))
            img.alpha_composite(lap)
    # pudar hitam di awal dan akhir
    f = min(prog(t, 0, 0.4), 1 - prog(t, DURASI - 0.5, 0.5))
    if f < 1:
        img = Image.blend(Image.new("RGBA", img.size, (0, 0, 0, 255)), img, f)
    return img.convert("RGB")


# ---------- muzik ----------
def buat_muzik(laluan):
    sr = 44100
    n = int(sr * DURASI)
    out = np.zeros(n)
    bpm = 112
    rentak = 60 / bpm

    def nota(f):
        return 440 * 2 ** ((f - 69) / 12)

    progres = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]  # Am F C G
    t_all = np.arange(n) / sr
    # pad kord
    for b in range(int(DURASI / (rentak * 4)) + 1):
        kord = progres[b % 4]
        s0 = int(b * rentak * 4 * sr)
        s1 = min(n, int((b + 1) * rentak * 4 * sr))
        if s0 >= n:
            break
        tt = t_all[s0:s1] - t_all[s0]
        env = np.minimum(1, tt / 0.3) * np.exp(-tt * 0.25)
        for m in kord:
            out[s0:s1] += 0.05 * env * (np.sin(2 * np.pi * nota(m) * tt) + 0.3 * np.sin(2 * np.pi * nota(m) * 2.003 * tt))
    # arpeggio pluck
    langkah = rentak / 2
    for k in range(int(DURASI / langkah)):
        b = int(k * langkah / (rentak * 4))
        kord = progres[b % 4]
        m = kord[[0, 1, 2, 1][k % 4]] + 12 + (12 if k % 8 == 6 else 0)
        s0 = int(k * langkah * sr)
        L = min(n - s0, int(0.5 * sr))
        tt = np.arange(L) / sr
        out[s0:s0 + L] += 0.09 * np.exp(-tt * 7) * np.sign(np.sin(2 * np.pi * nota(m) * tt)) * 0.5 \
            + 0.06 * np.exp(-tt * 5) * np.sin(2 * np.pi * nota(m) * tt)
    # kick & hi-hat (bermula selepas intro)
    noise = np.random.default_rng(1).uniform(-1, 1, n)
    for k in range(int(DURASI / rentak)):
        s0 = int(k * rentak * sr)
        if k * rentak < 2.6:
            continue
        L = min(n - s0, int(0.3 * sr))
        tt = np.arange(L) / sr
        fr = 50 + 90 * np.exp(-tt * 30)
        out[s0:s0 + L] += 0.35 * np.exp(-tt * 9) * np.sin(2 * np.pi * np.cumsum(fr) / sr)
        h0 = int((k + 0.5) * rentak * sr)
        if h0 < n:
            Lh = min(n - h0, int(0.06 * sr))
            out[h0:h0 + Lh] += 0.08 * np.exp(-np.arange(Lh) / sr * 60) * np.diff(noise[h0:h0 + Lh + 1])
    # pudar
    fade = np.minimum(1, np.minimum(t_all / 0.5, (DURASI - t_all) / 1.2))
    out *= np.clip(fade, 0, 1)
    out = np.tanh(out * 1.4) / np.tanh(1.4) * 0.8
    pcm = (out * 32767).astype(np.int16)
    stereo = np.repeat(pcm[:, None], 2, axis=1)
    with wave.open(laluan, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(stereo.tobytes())


def main():
    wav = FAIL_OUTPUT.rsplit(".", 1)[0] + "_muzik.wav"
    buat_muzik(wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", FAIL_OUTPUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(N):
        p.stdin.write(bingkai(i).tobytes())
        if i % 60 == 0:
            print(f"bingkai {i}/{N}", flush=True)
    p.stdin.close()
    p.wait()
    os.remove(wav)
    print("Siap:", FAIL_OUTPUT)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--pratonton":
        for s in sys.argv[2:]:
            bingkai(int(float(s) * FPS)).save(f"{os.path.dirname(FAIL_OUTPUT)}/pratonton_{s}.png")
    else:
        main()
