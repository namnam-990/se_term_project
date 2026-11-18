"""US-01 학생 회원가입 및 학교 이메일 인증 — FR-U-01 ~ 06 (Must / 5 SP)

회원가입·인증의 AC와 오류 처리를 검증한다.
"""

import re

import pytest

from app.models import AccountStatus, Role, User

VALID = {"student_no": "202299999", "email": "new@example.ac.kr", "password": "Passw0rd!"}


def _code_from_mail(mail) -> str:
    return re.search(r"\b(\d{6})\b", mail.sent[-1]["body"]).group(1)


def _token_from_mail(mail) -> str:
    return re.search(r"token=([\w\-]+)", mail.sent[-1]["body"]).group(1)


def test_us01_ac1_signup_creates_pending_and_sends_mail(client, db_session, mail):
    """Given 유효한 학번·이메일·비밀번호 When 가입 Then PENDING 생성 + 인증 메일(링크·6자리 코드)"""
    res = client.post("/api/auth/signup", json=VALID)
    assert res.status_code == 201
    assert res.json()["account_status"] == "PENDING"
    assert len(mail.sent) == 1 and mail.sent[0]["to"] == VALID["email"]
    assert _code_from_mail(mail)  # FR-U-02 6자리 코드
    assert _token_from_mail(mail)  # D-03 링크 토큰


def test_us01_ac2_verify_with_code_activates(client, db_session, mail):
    """Given PENDING + 인증 코드 When 인증 Then ACTIVE + ROLE_STUDENT (FR-U-04)"""
    client.post("/api/auth/signup", json=VALID)
    res = client.post(
        "/api/auth/email-verifications",
        json={"email": VALID["email"], "code": _code_from_mail(mail)},
    )
    assert res.status_code == 200
    user = db_session.query(User).filter_by(email=VALID["email"]).one()
    db_session.refresh(user)
    assert user.account_status == AccountStatus.ACTIVE
    assert user.role == Role.ROLE_STUDENT


def test_us01_ac2_verify_with_link_token(client, db_session, mail):
    """D-03: 메일 링크 토큰으로도 인증 가능"""
    client.post("/api/auth/signup", json=VALID)
    res = client.post("/api/auth/email-verifications", json={"token": _token_from_mail(mail)})
    assert res.status_code == 200


def test_us01_wrong_or_expired_code_rejected(client, mail, clock):
    """D-15: 틀린 코드 / 10분 경과 코드 → 400 INVALID_VERIFICATION"""
    client.post("/api/auth/signup", json=VALID)
    wrong_code = "000000" if _code_from_mail(mail) != "000000" else "111111"
    wrong = client.post(
        "/api/auth/email-verifications", json={"email": VALID["email"], "code": wrong_code}
    )
    assert wrong.status_code == 400 and wrong.json()["code"] == "INVALID_VERIFICATION"
    clock.advance(minutes=11)
    expired = client.post(
        "/api/auth/email-verifications",
        json={"email": VALID["email"], "code": _code_from_mail(mail)},
    )
    assert expired.status_code == 400


@pytest.mark.parametrize(
    "password",
    ["Pa0!", "Password!!", "Password12", "12345678!"],
    ids=["8자미만", "숫자없음", "특수문자없음", "영문없음"],
)
def test_us01_ac3_weak_password_rejected(client, password):
    """Given 8자 미만 또는 영문·숫자·특수문자 누락 When 가입 Then 400 + 규칙 안내 (FR-U-05)

    명세서는 '영문'만 요구 → 대소문자 조합은 검사하지 않음 ("password1!"은 통과)
    """
    res = client.post("/api/auth/signup", json={**VALID, "password": password})
    assert res.status_code == 400
    assert res.json()["code"] == "PASSWORD_POLICY"


def test_us01_ac4_duplicate_student_no_rejected(client, make_user):
    """Given 같은 학번 존재 When 가입 Then 409 DUPLICATE_STUDENT_NO (FR-U-06)"""
    make_user(VALID["student_no"], email="other@example.ac.kr")
    res = client.post("/api/auth/signup", json=VALID)
    assert res.status_code == 409 and res.json()["code"] == "DUPLICATE_STUDENT_NO"


def test_us01_ac4_duplicate_email_rejected(client, make_user):
    """Given 같은 이메일 존재 When 가입 Then 409 DUPLICATE_EMAIL (FR-U-06)"""
    make_user("202211111", email=VALID["email"])
    res = client.post("/api/auth/signup", json=VALID)
    assert res.status_code == 409 and res.json()["code"] == "DUPLICATE_EMAIL"
