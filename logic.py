"""Игровая логика «Нитей времени»: состояние, задания, награды, магазин.

Модуль не зависит от Flask: он принимает и меняет обычный dict-состояние
(его сервер хранит в JSON-файле игрока). Так логику легко тестировать
и потом перенести на другую платформу.

Уровень проходится ОДНИМ из трёх заданий на выбор: пазл 10x10, карточки, раскраска.
"""
import json
import random
from pathlib import Path

import content as C

BASE = Path(__file__).parent
PRIVATE = BASE / "data_private"                 # эталоны раскрасок: в браузер не отдаются
STATIC_COLOR = BASE / "static" / "img" / "color"
_cache = {}


class GameError(Exception):
    """Ошибка игрового действия; message показывается игроку."""
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def _json(path):
    if path not in _cache:
        _cache[path] = json.loads(Path(path).read_text(encoding="utf-8"))
    return _cache[path]


def color_answers(name):
    return _json(PRIVATE / f"color_{name}.json")            # {region_id: shade | None}


def color_regions(name):
    return {r["id"]: r for r in _json(STATIC_COLOR / f"{name}.json")["regions"]}


def new_state():
    return {
        "name": "", "sparks": 0, "threads": 0,
        "levels": {},          # "1-1": {"stars": 2, "tasks": {"puzzle": 2}} — лучшие результаты
        "claimed": [],         # единоразовые награды, чтобы не выдавать дважды
        "chapters_done": [], "artifacts": [], "pages": [],
        "items": [], "secrets": [], "run": None,
        "last": {},            # "1-1:puzzle": имя картинки, которую игрок прошёл последней
    }


# --- Доступность ---------------------------------------------------------------
def chapter_levels(cid):
    return sorted((lid for lid, lv in C.LEVELS.items() if lv["chapter"] == cid),
                  key=lambda lid: C.LEVELS[lid]["n"])


def chapter_unlocked(state, cid):
    return cid == 1 or (cid - 1) in state["chapters_done"]


def level_unlocked(state, lid):
    lv = C.LEVELS[lid]
    if not chapter_unlocked(state, lv["chapter"]):
        return False
    return lv["n"] == 1 or f'{lv["chapter"]}-{lv["n"] - 1}' in state["levels"]


def chapter_status(state, cid):
    if cid in state["chapters_done"]:
        return "done"
    if not chapter_unlocked(state, cid):
        return "locked"
    return "open" if chapter_levels(cid) else "soon"


# --- Награды ---------------------------------------------------------------------
def _claim(state, key, sparks):
    """Выдать награду один раз. Возвращает выданное число искорок (0, если уже была)."""
    if key in state["claimed"]:
        return 0
    state["claimed"].append(key)
    state["sparks"] += sparks
    return sparks


def stars_for(run):
    spent = run["mistakes"] + run["hints"]
    if spent == 0:
        return 3
    return 2 if spent <= 2 else 1


# --- Запуск задания ----------------------------------------------------------------
def _shuffle(n):
    order = list(range(n))
    while True:                                  # ни один кусочек не стоит на своём месте
        random.shuffle(order)
        if all(p != i for i, p in enumerate(order)):
            return order


def _pick(state, lid, task, pool):
    """Первый раз — первая картинка набора; при повторе — любая другая."""
    last = state.get("last", {}).get(f"{lid}:{task}")
    if last is None:
        return pool[0]
    return random.choice([x for x in pool if x != last] or pool)


def _new_run(state, lid, task):
    run = {"level": lid, "task": task, "mistakes": 0, "hints": 0}
    cfg = C.LEVELS[lid][task]
    if task == "puzzle":
        run["image"] = _pick(state, lid, "puzzle", cfg["images"])
        run["order"] = _shuffle(C.PUZZLE_GRID ** 2)
    elif task == "memory":
        ids = random.sample(list(C.CARDS), cfg["pairs"])
        deck = ids * 2
        random.shuffle(deck)
        run.update(deck=deck, found=[], open=[], misses=0)
    else:
        run["name"] = _pick(state, lid, "color", cfg["names"])
    return run


def public_task(lid, run):
    """Описание задания для браузера — без ответов."""
    task = run["task"]
    out = {"level": lid, "task": task, "title": C.TASKS[task]["title"],
           "reference": C.TASKS[task]["reference"], "hint_cost": C.HINT_COST}
    if task == "puzzle":
        out.update(image=f'/static/img/patterns/{run["image"]}.png', grid=C.PUZZLE_GRID, order=run["order"])
    elif task == "memory":
        out.update(pairs=len(run["deck"]) // 2, count=len(run["deck"]), found=run["found"], misses=run["misses"],
                   info={i: C.CARDS[i] for i in C.CARDS})
    else:
        name = run["name"]
        out.update(name=name, subtitle=C.CERAMICS[name], shades=C.SHADES,
                   json=f'/static/img/color/{name}.json', ref=f'/static/img/color/{name}_ref.png')
    return out


def start_task(state, lid, task):
    if lid not in C.LEVELS:
        raise GameError("Такого уровня нет.", 404)
    if not isinstance(task, str) or task not in C.TASKS:
        raise GameError("Такого задания нет.", 404)
    if not level_unlocked(state, lid):
        raise GameError("Сначала пройди предыдущий уровень.", 403)
    run = state.get("run")
    if not (run and run["level"] == lid and run["task"] == task):
        run = state["run"] = _new_run(state, lid, task)   # то же задание продолжается: счётчики не обнуляются
    if task == "memory":
        run["open"] = []                                  # недоигранный ход при возврате сбрасывается
    return public_task(lid, run)


def _run(state, lid):
    run = state.get("run")
    if not run or run["level"] != lid:
        raise GameError("Начни задание заново.", 409)
    return run


# --- Проверка входных данных -----------------------------------------------------------
def _valid_order(order):
    n = C.PUZZLE_GRID ** 2
    if (not isinstance(order, list) or len(order) != n
            or any(type(p) is not int for p in order) or set(order) != set(range(n))):
        raise GameError("Неверный порядок кусочков.")
    return order


def _valid_fills(fills, name):
    regs = color_regions(name)
    if not isinstance(fills, dict):
        raise GameError("Раскрась изделие.")
    for rid, shade in fills.items():
        if rid not in regs or shade not in C.SHADE_IDS + ["white"]:
            raise GameError("Неверная раскраска.")
    return fills


# --- Подсказки ----------------------------------------------------------------------------
def use_hint(state, lid, body):
    run = _run(state, lid)
    task = run["task"]
    if state["sparks"] < C.HINT_COST:
        raise GameError("Не хватает искорок для подсказки. Уровень можно пройти и без неё.", 402)

    if task == "puzzle":
        order = _valid_order(body.get("order"))
        pos = next((i for i, p in enumerate(order) if p != i), None)
        if pos is None:
            raise GameError("Все кусочки уже на местах.", 409)
        result = {"place": {"piece": pos, "pos": pos}}
    elif task == "memory":
        if run["open"]:
            raise GameError("Сначала закончи ход: переверни вторую карточку.", 409)
        left = {}
        for pos, cid in enumerate(run["deck"]):
            if pos not in run["found"]:
                left.setdefault(cid, []).append(pos)
        cid = random.choice(list(left))
        result = {"show": [{"pos": p, "card": cid} for p in left[cid]]}
    else:
        name = run["name"]
        fills = _valid_fills(body.get("fills") or {}, name)
        answers, regs = color_answers(name), color_regions(name)
        todo = [r for r in regs.values() if r["required"] and fills.get(r["id"]) != answers[r["id"]]]
        if not todo:
            raise GameError("Все области уже подобраны.", 409)
        r = max(todo, key=lambda r: r["area"])
        result = {"reveal": {"region": r["id"], "shade": answers[r["id"]]}}

    run["hints"] += 1
    state["sparks"] -= C.HINT_COST
    return {"text": C.TASKS[task]["hint_text"], "sparks": state["sparks"], **result}


# --- Проверка ответов ------------------------------------------------------------------------
def check_answer(state, lid, body):
    run = _run(state, lid)
    task = run["task"]

    if task == "puzzle":
        order = _valid_order(body.get("order"))
        if order == list(range(len(order))):
            return {"correct": True, "result": _finish(state, lid, run)}
        run["mistakes"] += 1
        return {"correct": False, "mistakes": run["mistakes"]}

    if task == "memory":
        pos = body.get("flip")
        deck = run["deck"]
        if type(pos) is not int or not 0 <= pos < len(deck):
            raise GameError("Такой карточки нет.")
        if pos in run["found"] or pos in run["open"]:
            raise GameError("Эта карточка уже открыта.", 409)
        if not run["open"]:
            run["open"] = [pos]
            return {"card": deck[pos]}
        first, run["open"] = run["open"][0], []
        if deck[first] != deck[pos]:
            run["misses"] += 1
            return {"card": deck[pos], "match": False, "first": first, "misses": run["misses"]}
        run["found"] += [first, pos]
        out = {"card": deck[pos], "match": True, "first": first, "misses": run["misses"]}
        if len(run["found"]) == len(deck):
            pairs = len(deck) // 2
            cap = 3 if run["misses"] <= pairs else 2 if run["misses"] <= 2 * pairs else 1
            out["result"] = _finish(state, lid, run, cap=cap, extra={"misses": run["misses"]})
        return out

    name = run["name"]
    fills = _valid_fills(body.get("fills"), name)
    answers, regs = color_answers(name), color_regions(name)
    if any(r["required"] and fills.get(r["id"], "white") == "white" for r in regs.values()):
        raise GameError("Раскрась все области: незакрашенные ещё остались.")
    total = score = 0.0
    for rid, master in answers.items():
        if not master:                       # белые области (фарфор) в оценке не участвуют
            continue
        area = regs[rid]["area"]
        total += area
        got = fills.get(rid, "white")
        if got == master:
            score += area
        elif got != "white" and abs(C.SHADE_IDS.index(got) - C.SHADE_IDS.index(master)) == 1:
            score += area * 0.5              # соседний оттенок — половина
    accuracy = score / total if total else 1.0
    cap = 3 if accuracy >= 0.8 else 2 if accuracy >= 0.6 else 1
    return {"correct": True, "result": _finish(state, lid, run, cap=cap, extra={"accuracy": round(accuracy * 100)})}


def _finish(state, lid, run, cap=None, extra=None):
    lv = C.LEVELS[lid]
    cid, task = lv["chapter"], run["task"]
    stars = stars_for(run)
    if cap:
        stars = min(stars, cap)
    rewards = []
    asset = run.get("image") or run.get("name")
    if asset:
        state.setdefault("last", {})[f"{lid}:{task}"] = asset

    first_pass = lid not in state["levels"]
    rec = state["levels"].setdefault(lid, {"stars": 0, "tasks": {}})
    rec["tasks"][task] = max(rec["tasks"].get(task, 0), stars)
    rec["stars"] = max(rec["tasks"].values())

    got = _claim(state, f"{lid}:base", C.REWARD_BASE[lv["n"]])
    if got:
        rewards.append({"label": "Уровень пройден", "sparks": got})
    if first_pass:
        _claim(state, f"{lid}:task:{task}", 0)
    else:
        got = _claim(state, f"{lid}:task:{task}", C.REWARD_OTHER_TASK)
        if got:
            rewards.append({"label": f'Новое задание: {C.TASKS[task]["title"]}', "sparks": got})

    if stars == 3:
        got = _claim(state, f"{lid}:extra", C.REWARD_EXTRA_GOAL)
        if got:
            rewards.append({"label": "Дополнительная цель: три звезды", "sparks": got})
        got = _claim(state, f"{lid}:stars3", C.REWARD_THREE_STARS)
        if got:
            rewards.append({"label": "Три звезды", "sparks": got})

    chapter_done = None
    if all(l in state["levels"] for l in chapter_levels(cid)) and cid not in state["chapters_done"]:
        state["chapters_done"].append(cid)
        got = _claim(state, f"ch{cid}:done", C.REWARD_CHAPTER)
        rewards.append({"label": "Глава завершена", "sparks": got})
        state["threads"] += 1
        page = C.ATLAS_PAGES.get(cid)
        if page:
            state["pages"].append(cid)
            state["artifacts"].append(cid)
        nxt = cid + 1 if cid < len(C.CHAPTERS) else None
        chapter_done = {
            "id": cid, "title": C.CHAPTERS[cid - 1]["title"],
            "artifact": page["artifact"] if page else None,
            "page": page["title"] if page else None,
            "next": nxt, "next_ready": bool(nxt and chapter_levels(nxt)),
        }

    state["run"] = None
    nxt_level = f'{cid}-{lv["n"] + 1}'
    return {
        "task": task, "stars": stars, "rewards": rewards,
        "total": sum(r["sparks"] for r in rewards),
        "mistakes": run["mistakes"], "hints": run["hints"],
        "next_level": nxt_level if nxt_level in C.LEVELS else None,
        "chapter_done": chapter_done, "sparks": state["sparks"], "threads": state["threads"],
        **(extra or {}),
    }


# --- Секреты и магазин ----------------------------------------------------------------------------
def find_secret(state, sid):
    sec = C.SECRETS.get(sid)
    if not sec:
        raise GameError("Здесь ничего нет.", 404)
    if not chapter_unlocked(state, sec["chapter"]):
        raise GameError("Глава ещё закрыта.", 403)
    if sid in state["secrets"]:
        return {"new": False, "text": "Эту подпись вы уже записали в Атлас.", "sparks": state["sparks"]}
    state["secrets"].append(sid)
    _claim(state, f"secret:{sid}", C.REWARD_SECRET)
    return {"new": True, "text": sec["text"], "reward": C.REWARD_SECRET, "sparks": state["sparks"]}


def buy(state, item_id):
    item = C.SHOP_BY_ID.get(item_id)
    if not item:
        raise GameError("Такого предмета нет.", 404)
    if item_id in state["items"]:
        raise GameError("Этот предмет уже у вас.", 409)
    if state["sparks"] < item["price"]:
        raise GameError(f'Не хватает {item["price"] - state["sparks"]} искорок.', 402)
    state["sparks"] -= item["price"]
    state["items"].append(item_id)
    return {"sparks": state["sparks"], "item": item_id}


# --- Состояние для интерфейса -----------------------------------------------------------------------
def public_state(state):
    chapters = []
    for ch in C.CHAPTERS:
        cid = ch["id"]
        levels = []
        for lid in chapter_levels(cid):
            lv = C.LEVELS[lid]
            rec = state["levels"].get(lid, {})
            levels.append({
                "id": lid, "title": lv["title"], "intro": lv["intro"],
                "stars": rec.get("stars", 0),
                "status": "done" if lid in state["levels"] else ("open" if level_unlocked(state, lid) else "locked"),
                "tasks": [{"id": t, "title": C.TASKS[t]["title"], "desc": C.TASKS[t]["desc"],
                           "stars": rec.get("tasks", {}).get(t, 0)} for t in C.TASK_ORDER],
            })
        chapters.append({
            **{k: ch[k] for k in ("id", "title", "region", "focus", "color", "story", "teaser")},
            "status": chapter_status(state, cid), "levels": levels,
            "stars": sum(l["stars"] for l in levels), "max_stars": 3 * len(levels),
        })
    atlas = []
    for ch in C.CHAPTERS:
        page = C.ATLAS_PAGES.get(ch["id"])
        open_ = ch["id"] in state["pages"]
        atlas.append({"chapter": ch["id"], "region": ch["region"], "unlocked": open_,
                      "title": page["title"] if (page and open_) else None,
                      "facts": page["facts"] if (page and open_) else []})
    return {
        "name": state["name"], "sparks": state["sparks"], "threads": state["threads"],
        "chapters": chapters, "atlas": atlas,
        "items": state["items"], "artifacts": state["artifacts"], "secrets": state["secrets"],
        "shop": [{**i, "owned": i["id"] in state["items"]} for i in C.SHOP],
        "hint_cost": C.HINT_COST,
    }
