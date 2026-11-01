"""Unhandled errors must not reach server logs with their message (guide §5·§6.4).

Runs the app under a real Uvicorn server: TestClient alone does not exercise the path
where Starlette re-raises after the 500 handler and Uvicorn logs the traceback.
"""

import json
import logging
import threading
import time
import urllib.error
import urllib.request

import uvicorn
from fastapi import FastAPI

from app.api.errors import register_exception_handlers

SECRET = "password=synthetic-secret-value"
SQL = "SELECT * FROM users WHERE email = 'leak@example.com'"


def _crash_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError(f"{SECRET} {SQL}")

    return app


def test_uvicorn_logs_only_the_exception_type(caplog):
    caplog.set_level(logging.DEBUG)
    config = uvicorn.Config(
        _crash_app(), host="127.0.0.1", port=0, log_config=None, lifespan="off", access_log=False
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            assert time.monotonic() < deadline, "uvicorn did not start"
            time.sleep(0.05)
        port = server.servers[0].sockets[0].getsockname()[1]
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/boom", timeout=5)
            raise AssertionError("expected HTTP 500")
        except urllib.error.HTTPError as exc:
            assert exc.code == 500
            body = json.loads(exc.read())
    finally:
        server.should_exit = True
        thread.join(timeout=10)

    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert "synthetic-secret" not in json.dumps(body)
    assert "synthetic-secret" not in caplog.text
    assert "SELECT" not in caplog.text
    assert "leak@example.com" not in caplog.text
    assert "RuntimeError" in caplog.text  # diagnosis keeps the exception type


def test_unhandled_error_is_not_re_raised_to_the_server():
    from fastapi.testclient import TestClient

    # Default TestClient re-raises server exceptions; a 500 response proves none escaped.
    response = TestClient(_crash_app()).get("/boom")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
