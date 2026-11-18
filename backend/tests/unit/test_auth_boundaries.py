"""US-01·02·03 보완: 재사용·만료·쿠키·CSRF·트랜잭션 경계 검증."""

import re
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.security import create_access_token, sha256, verify_password
from app.models import AccountStatus, AuthSession, EmailVerification, User
from tests.conftest import DEFAULT_PASSWORD

SIGNUP = {"student_no": "202299999", "email": "new@example.ac.kr", "password": "Passw0rd!"}


def login(client, login_id="202200001"):
    return client.post("/api/auth/login", json={"login_id": login_id, "password": DEFAULT_PASSWORD})


def refresh(client):
    return client.post(
        "/api/auth/refresh", headers={"X-CSRF-Token": client.cookies.get("csrf_token", "")}
    )


def test_signup_hashes_password_and_both_verification_secrets(client, db_session, mail):
    assert client.post("/api/auth/signup", json=SIGNUP).status_code == 201
    user = db_session.scalar(select(User).where(User.email == SIGNUP["email"]))
    assert user.password_hash != SIGNUP["password"]
    assert verify_password(SIGNUP["password"], user.password_hash)
    token = re.search(r"token=([\w-]+)", mail.sent[0]["body"])[1]
    code = re.search(r"\b(\d{6})\b", mail.sent[0]["body"])[1]
    digests = set(db_session.scalars(select(EmailVerification.token_hash)))
    assert digests == {sha256(token), sha256(f"{SIGNUP['email']}:{code}")}


@pytest.mark.parametrize("use_link", [True, False])
def test_verifying_one_secret_invalidates_both(client, mail, use_link):
    client.post("/api/auth/signup", json=SIGNUP)
    token = re.search(r"token=([\w-]+)", mail.sent[0]["body"])[1]
    code = re.search(r"\b(\d{6})\b", mail.sent[0]["body"])[1]
    link, manual = {"token": token}, {"email": SIGNUP["email"], "code": code}
    first, other = (link, manual) if use_link else (manual, link)
    assert client.post("/api/auth/email-verifications", json=first).status_code == 200
    for payload in (first, other):
        res = client.post("/api/auth/email-verifications", json=payload)
        assert res.status_code == 400 and res.json()["code"] == "INVALID_VERIFICATION"


def test_verification_expires_at_exact_deadline(client, clock, mail):
    client.post("/api/auth/signup", json=SIGNUP)
    token = re.search(r"token=([\w-]+)", mail.sent[0]["body"])[1]
    clock.advance(minutes=10)
    assert client.post("/api/auth/email-verifications", json={"token": token}).status_code == 400


def test_same_code_for_two_students_does_not_collide(client, monkeypatch):
    monkeypatch.setattr("app.services.auth_service.new_numeric_code", lambda: "123456")
    for number, email in [("202200010", "a@example.ac.kr"), ("202200011", "b@example.ac.kr")]:
        assert (
            client.post(
                "/api/auth/signup", json={**SIGNUP, "student_no": number, "email": email}
            ).status_code
            == 201
        )
        assert (
            client.post(
                "/api/auth/email-verifications", json={"email": email, "code": "123456"}
            ).status_code
            == 200
        )


def test_zero_code_is_a_valid_generated_code(client, mail, monkeypatch):
    # 기존 테스트가 오답으로 고정했던 000000도 정상 발급될 수 있다.
    monkeypatch.setattr("app.services.auth_service.new_numeric_code", lambda: "000000")
    assert client.post("/api/auth/signup", json=SIGNUP).status_code == 201
    assert "000000" in mail.sent[0]["body"]
    res = client.post(
        "/api/auth/email-verifications", json={"email": SIGNUP["email"], "code": "000000"}
    )
    assert res.status_code == 200


def test_school_domain_and_case_insensitive_duplicate(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "allowed_email_domain", "example.ac.kr")
    assert (
        client.post("/api/auth/signup", json={**SIGNUP, "email": "new@elsewhere.com"}).json()[
            "code"
        ]
        == "EMAIL_DOMAIN"
    )
    assert client.post("/api/auth/signup", json=SIGNUP).status_code == 201
    res = client.post(
        "/api/auth/signup", json={**SIGNUP, "student_no": "202288888", "email": "NEW@example.ac.kr"}
    )
    assert res.status_code == 409 and res.json()["code"] == "DUPLICATE_EMAIL"


def test_mail_failure_rolls_back_signup_and_allows_retry(client, db_session, mail, monkeypatch):
    original = mail.send

    def fail(*args):
        raise OSError("SMTP unavailable")

    monkeypatch.setattr(mail, "send", fail)
    res = client.post("/api/auth/signup", json=SIGNUP)
    assert res.status_code == 503 and res.json()["code"] == "MAIL_DELIVERY_FAILED"
    assert db_session.scalar(select(func.count()).select_from(User)) == 0
    assert db_session.scalar(select(func.count()).select_from(EmailVerification)) == 0
    monkeypatch.setattr(mail, "send", original)
    assert client.post("/api/auth/signup", json=SIGNUP).status_code == 201


def test_bcrypt_limit_is_validated_without_server_error(client):
    res = client.post("/api/auth/signup", json={**SIGNUP, "password": "Aa1!" + "가" * 24})
    assert res.status_code == 400 and res.json()["code"] == "PASSWORD_POLICY"


def test_cookie_flags_and_refresh_secret_not_in_response(client, make_user):
    make_user()
    res = login(client)
    assert "refresh_token" not in res.json()
    cookies = res.headers.get_list("set-cookie")
    for name in ("access_token", "refresh_token"):
        header = next(c for c in cookies if c.startswith(name + "="))
        assert "HttpOnly" in header and "SameSite=lax" in header and "Path=/" in header
    csrf = next(c for c in cookies if c.startswith("csrf_token="))
    assert "HttpOnly" not in csrf and "Max-Age=604800" in csrf
    assert client.get("/api/auth/me").status_code == 200


def test_secure_cookies_when_configured(client, make_user, monkeypatch):
    make_user()
    monkeypatch.setattr(get_settings(), "cookie_secure", True)
    assert all("Secure" in c for c in login(client).headers.get_list("set-cookie"))


def test_cookie_logout_requires_csrf_and_revokes_refresh(client, make_user):
    make_user()
    login(client)
    old_refresh, old_csrf = client.cookies["refresh_token"], client.cookies["csrf_token"]
    assert client.post("/api/auth/logout").status_code == 403
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/logout", headers={"X-CSRF-Token": old_csrf}).status_code == 200
    assert not any(
        name in client.cookies for name in ("access_token", "refresh_token", "csrf_token")
    )
    client.cookies.set("refresh_token", old_refresh)
    client.cookies.set("csrf_token", old_csrf)
    assert refresh(client).json()["code"] == "SESSION_REVOKED"


def test_refresh_with_expired_access_does_not_extend_session(client, db_session, make_user):
    user = make_user()
    first = login(client)
    session = db_session.scalar(select(AuthSession))
    expiry, refresh_cookie = session.expires_at, client.cookies["refresh_token"]
    expired = create_access_token(
        user.id, user.role.value, session.id, now=datetime.now(UTC) - timedelta(hours=2)
    )
    client.cookies.clear()
    client.cookies.set("access_token", expired)
    client.cookies.set("refresh_token", refresh_cookie)
    client.cookies.set("csrf_token", "test-csrf")
    assert client.get("/api/auth/me").status_code == 401
    result = refresh(client)
    assert result.status_code == 200
    assert result.json()["access_token"] != first.json()["access_token"]
    assert client.get("/api/auth/me").status_code == 200
    db_session.refresh(session)
    assert session.expires_at == expiry and client.cookies["refresh_token"] == refresh_cookie


def test_refresh_preserves_csrf_for_parallel_protected_requests(client, make_user):
    make_user()
    login(client)
    original_csrf = client.cookies["csrf_token"]
    assert refresh(client).status_code == 200
    # 다른 탭·동시 요청은 갱신 전 읽은 CSRF 헤더를 보낼 수 있다.
    assert (
        client.post("/api/auth/logout", headers={"X-CSRF-Token": original_csrf}).status_code == 200
    )


def test_refresh_expired_session_and_missing_csrf(client, clock, make_user):
    make_user()
    login(client)
    assert client.post("/api/auth/refresh").status_code == 403
    clock.advance(days=7)
    assert refresh(client).json()["code"] == "SESSION_REVOKED"


@pytest.mark.parametrize("status", [AccountStatus.PENDING, AccountStatus.LOCKED])
def test_refresh_rechecks_account_status(client, db_session, make_user, status):
    user = make_user()
    login(client)
    user.account_status = status
    db_session.commit()
    result = refresh(client)
    assert result.status_code == 403 and result.json()["code"] == f"ACCOUNT_{status}"


def test_logout_only_revokes_current_session(client, make_user):
    make_user()
    first, second = login(client).json()["access_token"], login(client).json()["access_token"]
    assert (
        client.post("/api/auth/logout", headers={"Authorization": f"Bearer {second}"}).status_code
        == 200
    )
    assert (
        client.get("/api/auth/me", headers={"Authorization": f"Bearer {first}"}).status_code == 200
    )
    assert (
        client.get("/api/auth/me", headers={"Authorization": f"Bearer {second}"}).status_code == 401
    )


def test_user_cannot_use_another_users_session(client, db_session, make_user):
    owner, other = make_user(), make_user("202200002")
    login(client)
    session = db_session.scalar(select(AuthSession).where(AuthSession.user_id == owner.id))
    token = create_access_token(other.id, other.role.value, session.id)
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401 and res.json()["code"] == "TOKEN_INVALID"


def test_signed_token_missing_required_claims_is_401(client):
    settings = get_settings()
    token = jwt.encode(
        {"sub": "1", "typ": "access"}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    assert (
        client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    )
