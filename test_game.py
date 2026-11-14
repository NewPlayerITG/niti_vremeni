"""Проверка игровой логики и API без браузера: python test_game.py"""
import json
import os
import tempfile

os.environ["NITI_DATA"] = tempfile.mkdtemp()           # тесты не трогают настоящий прогресс

import content as C
import logic
from app import app


def expect_error(fn, status):
    try:
        fn()
    except logic.GameError as e:
        assert e.status == status, (e.status, status)
        return
    raise AssertionError("ожидалась ошибка")


def solve_memory(state, lid, misses=0):
    """Проходит игру на пары (колода берётся из служебного состояния сервера); misses — число промахов."""
    deck = list(state["run"]["deck"])
    first = {}
    for pos, cid in enumerate(deck):
        first.setdefault(cid, []).append(pos)
    pairs = list(first.values())
    for _ in range(misses):                      # сознательные промахи: две разные карточки
        logic.check_answer(state, lid, {"flip": pairs[0][0]})
        r = logic.check_answer(state, lid, {"flip": pairs[1][0]})
        assert r["match"] is False
    res = None
    for a, b in pairs:
        r1 = logic.check_answer(state, lid, {"flip": a})
        assert "match" not in r1 and r1["card"] == deck[a]
        res = logic.check_answer(state, lid, {"flip": b})
        assert res["match"] is True
    return res["result"]


def paint_like_master(state):
    name = state["run"]["name"]
    ans, regs = logic.color_answers(name), logic.color_regions(name)
    return {rid: s for rid, s in ans.items() if s and regs[rid]["required"]}


def test_logic():
    n = C.PUZZLE_GRID ** 2
    assert n == 25
    s = logic.new_state()
    expect_error(lambda: logic.start_task(s, "1-2", "puzzle"), 403)       # уровни идут по порядку
    expect_error(lambda: logic.start_task(s, "1-1", "dance"), 404)
    expect_error(lambda: logic.start_task(s, "1-1", ["x"]), 404)

    # --- пазл 5x5 ---
    t = logic.start_task(s, "1-1", "puzzle")
    assert t["grid"] == 5 and sorted(t["order"]) == list(range(n))
    assert t["image"].endswith("/p1.png"), "первый раз — первая картинка набора"
    assert all(p != i for i, p in enumerate(t["order"])), "ни один кусочек не должен стоять сразу на месте"
    assert "answer" not in json.dumps(t)
    expect_error(lambda: logic.check_answer(s, "1-1", {"order": [0, 1]}), 400)
    r = logic.check_answer(s, "1-1", {"order": t["order"]})
    assert r["correct"] is False and r["mistakes"] == 1
    expect_error(lambda: logic.use_hint(s, "1-1", {"order": t["order"]}), 402)   # нет искорок
    r = logic.check_answer(s, "1-1", {"order": list(range(n))})
    assert r["correct"] and r["result"]["stars"] == 2 and r["result"]["total"] == 50, r

    # повтор: ДРУГАЯ картинка; без ошибок — только бонусы за звёзды; ещё раз — ничего
    t2 = logic.start_task(s, "1-1", "puzzle")
    assert t2["image"] != t["image"], "при повторе должна быть другая картинка"
    r = logic.check_answer(s, "1-1", {"order": list(range(n))})["result"]
    assert r["stars"] == 3 and r["total"] == 25, r
    t3 = logic.start_task(s, "1-1", "puzzle")
    assert t3["image"] != t2["image"]
    assert logic.check_answer(s, "1-1", {"order": list(range(n))})["result"]["total"] == 0

    # --- найди пару: 4 пары ---
    t = logic.start_task(s, "1-1", "memory")
    assert t["pairs"] == 4 and t["count"] == 8 and t["found"] == []
    assert "deck" not in json.dumps(t), "расклад карточек в браузер не уходит"
    run = s["run"]
    assert sorted(run["deck"]) == sorted(list(set(run["deck"])) * 2) and len(set(run["deck"])) == 4
    expect_error(lambda: logic.check_answer(s, "1-1", {"flip": 99}), 400)
    logic.check_answer(s, "1-1", {"flip": 0})
    expect_error(lambda: logic.check_answer(s, "1-1", {"flip": 0}), 409)    # та же карточка дважды
    expect_error(lambda: logic.use_hint(s, "1-1", {}), 409)   # ход не закончен
    s["run"]["open"] = []
    res = solve_memory(s, "1-1")
    assert res["total"] == C.REWARD_OTHER_TASK and res["stars"] == 3 and res["misses"] == 0, res
    assert s["sparks"] == 50 + 25 + 20, s["sparks"]

    # --- 1-2: раскраска по образцу мастера и подсказка ---
    t = logic.start_task(s, "1-2", "color")
    assert t["task"] == "color" and len(t["shades"]) == 4 and t["name"] == "bird"
    assert "answer" not in json.dumps(t)
    fills = paint_like_master(s)
    first = next(iter(fills))
    partial = {k: v for k, v in fills.items() if k != first}
    expect_error(lambda: logic.check_answer(s, "1-2", {"fills": partial}), 400)   # не всё закрашено
    expect_error(lambda: logic.check_answer(s, "1-2", {"fills": {"zzz": "s1"}}), 400)
    h = logic.use_hint(s, "1-2", {"fills": partial})
    assert h["reveal"]["region"] and s["sparks"] == 95 - 30
    r = logic.check_answer(s, "1-2", {"fills": fills})["result"]
    assert r["accuracy"] >= 95 and r["stars"] == 2 and r["total"] == 70, r      # подсказка -> 2 звезды
    t = logic.start_task(s, "1-2", "color")
    assert t["name"] != "bird", "при повторе раскраска другая"

    # --- 1-3: промахи в памяти ---
    t = logic.start_task(s, "1-3", "memory")
    assert t["pairs"] == 6 and t["count"] == 12
    # подсказка показывает пару, но ничего не открывает; ход должен быть закончен
    s["sparks"] += 30
    h = logic.use_hint(s, "1-3", {})
    assert len(h["show"]) == 2 and h["show"][0]["card"] == h["show"][1]["card"]
    res = solve_memory(s, "1-3", misses=13)             # > 2 * 6 промахов -> 1 звезда; подсказка тоже учтена
    assert res["stars"] == 1 and res["misses"] == 13, res
    # уровень пройден последним из трёх -> глава закончена
    assert res["chapter_done"]["id"] == 1 and res["chapter_done"]["next"] == 2, res
    st = logic.public_state(s)
    assert st["threads"] == 1 and st["chapters"][0]["status"] == "done"
    assert st["chapters"][1]["status"] == "soon"
    assert st["artifacts"] == [1] and st["atlas"][0]["unlocked"]
    assert [t["stars"] > 0 for t in st["chapters"][0]["levels"][0]["tasks"]] == [True, True, False]

    # хорошая игра: 6 пар и <=6 промахов -> 3 звезды
    logic.start_task(s, "1-3", "memory")
    assert solve_memory(s, "1-3", misses=3)["stars"] == 3

    # секрет и магазин
    a, b = logic.find_secret(s, "gzhel-signature"), logic.find_secret(s, "gzhel-signature")
    assert a["new"] and not b["new"]
    s["sparks"] += 500
    logic.buy(s, "lamp")
    expect_error(lambda: logic.buy(s, "lamp"), 409)


def test_resume_keeps_counters():
    """Выход из задания и повторный вход не обнуляют ошибки (нельзя «сбросить» счёт)."""
    s = logic.new_state()
    t1 = logic.start_task(s, "1-1", "puzzle")
    logic.check_answer(s, "1-1", {"order": t1["order"]})
    t2 = logic.start_task(s, "1-1", "puzzle")
    assert t2["order"] == t1["order"] and t2["image"] == t1["image"] and s["run"]["mistakes"] == 1
    m1 = logic.start_task(s, "1-1", "memory")                 # найденные пары сохраняются
    deck = s["run"]["deck"]
    a = deck.index(deck[0]); b = deck.index(deck[0], a + 1)
    logic.check_answer(s, "1-1", {"flip": a}); logic.check_answer(s, "1-1", {"flip": b})
    m2 = logic.start_task(s, "1-1", "memory")
    assert sorted(m2["found"]) == sorted([a, b]) and s["run"]["open"] == []


def test_api():
    c = app.test_client()
    post = lambda p, j=None: c.post("/api/" + p, json=j if j is not None else {})
    assert post("reset").status_code == 200
    assert post("start", {"name": "Аня"}).get_json()["name"] == "Аня"
    assert post("level/1-2/start", {"task": "puzzle"}).status_code == 403
    assert post("level/1-1/start", {"task": "nope"}).status_code == 404
    assert post("level/1-1/start", {}).status_code == 404
    d = post("level/1-1/start", {"task": "puzzle"}).get_json()
    assert d["task"]["grid"] == 5 and len(d["task"]["order"]) == 25
    r = post("level/1-1/check", {"order": list(range(25))}).get_json()
    assert r["correct"] and r["result"]["stars"] == 3 and r["result"]["total"] == 75
    assert post("level/1-1/check", {"order": list(range(25))}).status_code == 409   # задание уже закрыто
    st = c.get("/api/state").get_json()
    assert st["sparks"] == 75 and st["chapters"][0]["levels"][1]["status"] == "open"
    assert post("shop/buy", {"item": "frame"}).status_code == 402   # у игрока 75, рамка стоит 100
    # прогресс лежит в файле, а не в cookie; чужой cookie без подписи не работает
    assert len(list(__import__("pathlib").Path(os.environ["NITI_DATA"]).glob("*.json"))) >= 1
    assert "sparks" not in c.get_cookie("session").value if c.get_cookie("session") else True
    c2 = app.test_client()
    assert c2.get("/api/state").get_json()["sparks"] == 0


def test_assets():
    from pathlib import Path
    root = Path(__file__).parent / "static" / "img"
    for i in range(1, 9):
        assert (root / "motifs" / f"m{i}.png").exists() and (root / "patterns" / f"p{i}.png").exists()
    for lv in C.LEVELS.values():
        for img in lv["puzzle"]["images"]:
            assert (root / "patterns" / f"{img}.png").exists()
        for n in lv["color"]["names"]:
            assert (root / "color" / f"{n}.json").exists() and (root / "color" / f"{n}_ref.png").exists()
            assert n in C.CERAMICS
        assert 2 * lv["memory"]["pairs"] <= 2 * len(C.CARDS) and len(lv["puzzle"]["images"]) >= 2


if __name__ == "__main__":
    test_assets(); test_logic(); test_resume_keeps_counters(); test_api()
    print("OK: вся логика и API проходят")
