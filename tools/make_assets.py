"""Нарезает исходные картинки и готовит раскраски. Запуск из корня проекта: python tools/make_assets.py"""
import json, sys
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).parent))
from segment import segment

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src_img"
OUT = ROOT / "static" / "img"
DATA = ROOT / "data_private"
for d in (OUT / "patterns", OUT / "motifs", OUT / "color", DATA):
    d.mkdir(parents=True, exist_ok=True)

TW, TH = 370, 500          # размер плитки: 37 x 50 пикселей на кусочек пазла 10x10

# --- пазлы: 8 узоров ---
pat = Image.open(SRC / "patterns.png").convert("RGB")
XS, YS = [5, 393, 774, 1159], [5, 521]
for i in range(8):
    x0, y0 = XS[i % 4], YS[i // 4]
    pat.crop((x0, y0, x0 + TW, y0 + TH)).save(OUT / "patterns" / f"p{i+1}.png", optimize=True)

# --- карточки: 8 элементов росписи ---
mot = Image.open(SRC / "motifs.png").convert("RGB")
for i in range(8):
    x0, y0 = 384 * (i % 4) + 7, 512 * (i // 4) + 6
    tile = mot.crop((x0, y0, x0 + TW, y0 + TH))
    tile.save(OUT / "motifs" / f"m{i+1}.png", optimize=True)

# --- раскраски: номер плитки -> имя ---
COLOR = {"bud": 7, "bird": 2, "vase": 3, "teapot": 6}
for name, num in COLOR.items():
    tmp = OUT / "color" / f"{name}_ref.png"
    mot.crop((384 * ((num - 1) % 4) + 7, 512 * ((num - 1) // 4) + 6,
              384 * ((num - 1) % 4) + 7 + TW, 512 * ((num - 1) // 4) + 6 + TH)).save(tmp, optimize=True)
    seg = segment(tmp)
    regs = seg["regions"]
    total = sum(r["area"] for r in regs if r["shade"]) or 1
    x0, y0, x1, y1 = seg["bbox"]
    pad = 24                                   # поля вокруг рисунка, чтобы он занимал весь экран
    vb = [max(0, x0 - pad), max(0, y0 - pad), min(seg["w"], x1 + pad) - max(0, x0 - pad), min(seg["h"], y1 + pad) - max(0, y0 - pad)]
    public = {"w": seg["w"], "h": seg["h"], "vb": vb, "regions": [
        {"id": r["id"], "d": r["d"], "area": r["area"],
         # крошечные области можно оставить пустыми
         "required": bool(r["shade"]) and r["area"] / total >= 0.004}
        for r in regs]}
    (OUT / "color" / f"{name}.json").write_text(json.dumps(public, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    answers = {r["id"]: r["shade"] for r in regs}
    (DATA / f"color_{name}.json").write_text(json.dumps(answers), encoding="utf-8")
    print(name, "областей:", len(regs), "обязательных:", sum(p["required"] for p in public["regions"]))
print("Готово")
