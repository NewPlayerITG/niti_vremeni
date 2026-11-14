"""Сервер «Нитей времени» (Flask). Запуск: python app.py → http://localhost:5000

Прогресс игроков хранится в JSON-файлах (instance/players/<id>.json); в cookie — только подписанный id.
Переменные окружения: PORT, HOST (по умолчанию 0.0.0.0 — чтобы открывать с телефона),
NITI_SECRET (ключ подписи cookie), NITI_DATA (папка прогресса), NITI_DEBUG=1 (режим отладки; только локально!).
"""
import json
import os
import re
import threading
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, session

import logic

BASE = Path(__file__).parent
INSTANCE = BASE / "instance"
PLAYERS = Path(os.environ.get("NITI_DATA", INSTANCE / "players"))
PLAYERS.mkdir(parents=True, exist_ok=True)
PID_RE = re.compile(r"^[0-9a-f]{32}$")
LOCK = threading.Lock()

app = Flask(__name__)


def _secret_key():
    env = os.environ.get("NITI_SECRET")
    if env:
        return env
    f = INSTANCE / "secret_key"
    if not f.exists():
        INSTANCE.mkdir(exist_ok=True)
        f.write_text(os.urandom(32).hex())
        try:
            f.chmod(0o600)
        except OSError:
            pass
    return f.read_text().strip()


app.secret_key = _secret_key()
app.config.update(SESSION_COOKIE_SAMESITE="Lax", PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 365)


def _file(pid):
    return PLAYERS / f"{pid}.json"


def load_state(pid):
    try:
        data = json.loads(_file(pid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return logic.new_state()
    return {**logic.new_state(), **data}


def save_state(pid, state):
    tmp = _file(pid).with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, _file(pid))


def action(fn):
    """Обёртка: достаёт состояние игрока, ловит GameError, сохраняет результат."""
    def wrapper(*args, **kwargs):
        pid = session.get("pid")
        if not (isinstance(pid, str) and PID_RE.match(pid)):
            pid = session["pid"] = uuid.uuid4().hex
        session.permanent = True
        with LOCK:
            state = load_state(pid)
            try:
                out = fn(state, *args, **kwargs)
            except logic.GameError as e:
                return jsonify({"error": e.message}), e.status
            save_state(pid, state)
        return jsonify(out)
    wrapper.__name__ = fn.__name__
    return wrapper


def body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/state")
@action
def api_state(state):
    return logic.public_state(state)


@app.post("/api/start")
@action
def api_start(state):
    name = str(body().get("name", "")).strip()[:20]
    if not name:
        raise logic.GameError("Введите имя.")
    state["name"] = name
    return logic.public_state(state)


@app.post("/api/level/<lid>/start")
@action
def api_level_start(state, lid):
    task = logic.start_task(state, lid, body().get("task"))
    return {"task": task, "sparks": state["sparks"]}


@app.post("/api/level/<lid>/hint")
@action
def api_level_hint(state, lid):
    return logic.use_hint(state, lid, body())


@app.post("/api/level/<lid>/check")
@action
def api_level_check(state, lid):
    return logic.check_answer(state, lid, body())


@app.post("/api/secret/<sid>")
@action
def api_secret(state, sid):
    return logic.find_secret(state, sid)


@app.post("/api/shop/buy")
@action
def api_buy(state):
    return logic.buy(state, body().get("item"))


@app.post("/api/reset")
@action
def api_reset(state):
    state.clear()
    state.update(logic.new_state())
    return logic.public_state(state)


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", 5000)),
            debug=os.environ.get("NITI_DEBUG") == "1")
