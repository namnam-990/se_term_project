"""GET /api/policies/current — 설계서 4장, FR-R-03 표시용 (구현 완료)."""


def test_current_policy_returns_spec_defaults(client, policy, make_user, auth_headers):
    res = client.get("/api/policies/current", headers=auth_headers(make_user()))
    assert res.status_code == 200
    body = res.json()
    assert body["exam_mode"] is False
    assert (body["days_ahead"], body["max_hours"]) == (7, 4)  # FR-A-20 평상시


def test_current_policy_exam_mode(client, db_session, policy, make_user, auth_headers):
    policy.exam_mode = True
    db_session.commit()
    body = client.get("/api/policies/current", headers=auth_headers(make_user())).json()
    assert (body["days_ahead"], body["max_hours"]) == (1, 3)  # FR-A-20 시험 기간


def test_current_policy_requires_login(client, policy):
    assert client.get("/api/policies/current").status_code == 401
