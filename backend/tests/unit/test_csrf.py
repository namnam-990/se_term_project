from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.csrf import CSRF_COOKIE, CSRF_HEADER, verify_csrf
from app.core.exceptions import AppError, app_error_handler

app = FastAPI()
app.add_exception_handler(AppError, app_error_handler)


@app.post("/x", dependencies=[Depends(verify_csrf)])
def x():
    return {"ok": True}


client = TestClient(app)


def test_csrf_rejects_missing_header():
    client.cookies.set(CSRF_COOKIE, "abc")
    res = client.post("/x")
    assert res.status_code == 403
    assert res.json()["code"] == "CSRF_FAILED"


def test_csrf_accepts_matching_cookie_and_header():
    client.cookies.set(CSRF_COOKIE, "abc")
    assert client.post("/x", headers={CSRF_HEADER: "abc"}).status_code == 200


def test_csrf_skipped_for_bearer():
    client.cookies.clear()
    assert client.post("/x", headers={"Authorization": "Bearer t"}).status_code == 200
