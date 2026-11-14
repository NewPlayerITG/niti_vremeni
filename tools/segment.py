"""Разбиение акварельной иллюстрации на области для раскраски."""
import numpy as np, cv2
from scipy import ndimage as ndi
from PIL import Image

# пороги по красному каналу: чем темнее, тем насыщеннее кобальт
THRESH = [62, 108, 170, 232]          # dark | mid | light | pale | white
SHADES = ["s4", "s3", "s2", "s1", None]   # s4 — самый тёмный; None — фарфор (белый)
SCALE = 2


def segment(path, min_area=140, min_thick=2.6):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    im2 = im.resize((w * SCALE, h * SCALE), Image.LANCZOS)
    R = cv2.GaussianBlur(np.asarray(im2)[:, :, 0].astype(np.float32), (0, 0), 0.9)
    level = np.digitize(R, THRESH)             # 0 dark ... 4 white
    H, W = level.shape

    labels = np.zeros((H, W), np.int32)
    info = {}                                   # label -> (level, area, thick)
    nxt = 1
    for lv in range(5):
        lab, n = ndi.label(level == lv)
        if not n:
            continue
        dist = ndi.distance_transform_edt(lab > 0)
        areas = ndi.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1))
        thick = ndi.maximum(dist, lab, index=np.arange(1, n + 1))
        for k in range(1, n + 1):
            labels[lab == k] = nxt
            info[nxt] = (lv, int(areas[k - 1]), float(thick[k - 1]))
            nxt += 1

    # фон: самая большая белая компонента, касающаяся края
    border = set(np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]])))
    bg_cands = [l for l in border if info[l][0] == 4]
    bg = max(bg_cands, key=lambda l: info[l][1])

    good = np.zeros(nxt, bool)
    for l, (lv, a, t) in info.items():
        good[l] = (l == bg) or (a >= min_area and t >= min_thick)
    gm = good[labels]
    idx = ndi.distance_transform_edt(~gm, return_distances=False, return_indices=True)
    labels = labels[idx[0], idx[1]]

    # области
    regions = []
    ids = [l for l in np.unique(labels) if l != bg]
    ids.sort(key=lambda l: (np.where(labels == l)[0].min(), np.where(labels == l)[1].min()))
    for n, l in enumerate(ids, 1):
        mask = (labels == l).astype(np.uint8)
        cnts, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        d = []
        for c in cnts:
            c = cv2.approxPolyDP(c, 0.8, True)
            if len(c) < 3:
                continue
            pts = c[:, 0, :]
            d.append("M" + "L".join(f"{x} {y}" for x, y in pts) + "Z")
        if not d:
            continue
        regions.append({"id": f"r{n}", "d": "".join(d), "area": int(mask.sum()),
                        "shade": SHADES[info[l][0]], "label": int(l)})
    ys, xs = np.where(labels != bg)
    bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    return {"w": W, "h": H, "regions": regions, "labels": labels, "bg": int(bg), "bbox": bbox}
