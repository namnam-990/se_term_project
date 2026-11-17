from datetime import datetime

import pytest

from app.core.deps import require_student
from app.main import app
from app.models import (
    AccountStatus,
    OperationPolicy,
    Reservation,
    ReservationStatus,
    Role,
    Seat,
    User,
)


def at(hour):
    return datetime(2026, 11, 20, hour)


def setup_student(db, login_id):
    user = User(
        login_id=login_id,
        password_hash="unused",
        role=Role.ROLE_STUDENT,
        account_status=AccountStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    return user


def test_us04_grid_states_and_time_changes(client, db_session):
    me = setup_student(db_session, "me")
    other = setup_student(db_session, "other")
    app.dependency_overrides[require_student] = lambda: me
    db_session.add(OperationPolicy(id=1))
    for i in range(1, 6):
        db_session.add(Seat(id=i, seat_number=f"A-{i:02d}", grid_row=1, grid_col=i, enabled=i < 5))
    db_session.flush()
    for seat_id, user, status, end in [
        (1, other, ReservationStatus.RESERVED, 10),
        (2, other, ReservationStatus.CHECKED_IN, 11),
        (3, me, ReservationStatus.RESERVED, 11),
        (4, other, ReservationStatus.RESERVED, 11),
    ]:
        db_session.add(
            Reservation(
                seat_id=seat_id, user_id=user.id, start_at=at(9), end_at=at(end), status=status
            )
        )
    db_session.commit()

    def statuses(start, end):
        response = client.get(
            "/api/seats",
            params={"start_at": at(start).isoformat(), "end_at": at(end).isoformat()},
        )
        assert response.status_code == 200
        return [seat["status"] for seat in response.json()["seats"]]

    assert statuses(10, 11) == ["AVAILABLE", "IN_USE", "MINE", "RESERVED"]
    assert statuses(11, 12) == ["AVAILABLE"] * 4


def test_us04_policy_window_and_slot_validation(client, db_session):
    me = setup_student(db_session, "me")
    app.dependency_overrides[require_student] = lambda: me
    db_session.add(OperationPolicy(id=1, exam_mode=True))
    db_session.commit()
    for start, end, code in [
        ("2026-11-19T10:00", "2026-11-19T11:00", "OUT_OF_BOOKING_WINDOW"),
        ("2026-11-22T10:00", "2026-11-22T11:00", "OUT_OF_BOOKING_WINDOW"),
        ("2026-11-20T10:30", "2026-11-20T11:00", "INVALID_TIME_RANGE"),
        ("2026-11-20T21:00", "2026-11-20T23:00", "INVALID_TIME_RANGE"),
        ("2026-11-20T10:00+09:00", "2026-11-20T11:00+09:00", "INVALID_TIME_RANGE"),
    ]:
        response = client.get("/api/seats", params={"start_at": start, "end_at": end})
        assert response.status_code == 400
        assert response.json()["code"] == code


def test_us06_history_is_private_sorted_and_filterable(client, db_session):
    me = setup_student(db_session, "me")
    other = setup_student(db_session, "other")
    app.dependency_overrides[require_student] = lambda: me
    db_session.add(Seat(id=1, seat_number="A-01", grid_row=1, grid_col=1))
    db_session.flush()
    for id_, user, status, created in [
        (1, me, ReservationStatus.RESERVED, 9),
        (2, me, ReservationStatus.CANCELLED, 10),
        (3, other, ReservationStatus.RESERVED, 11),
    ]:
        db_session.add(
            Reservation(
                id=id_,
                user_id=user.id,
                seat_id=1,
                start_at=at(13),
                end_at=at(14),
                status=status,
                created_at=at(created),
            )
        )
    db_session.commit()

    def get_history(status=None):
        params = {"status": status} if status else {}
        response = client.get("/api/me/reservations", params=params)
        assert response.status_code == 200
        return response.json()

    rows = get_history()["items"]
    assert [row["id"] for row in rows] == [2, 1]
    assert [row["seat_number"] for row in rows] == ["A-01", "A-01"]
    assert [row["id"] for row in get_history("RESERVED")["items"]] == [1]
    assert get_history("COMPLETED") == {"items": [], "message": "선택한 상태의 예약이 없습니다."}


def test_us04_current_slot_can_be_viewed_until_it_ends(client, db_session, clock):
    me = setup_student(db_session, "me")
    other = setup_student(db_session, "other")
    app.dependency_overrides[require_student] = lambda: me
    db_session.add_all(
        [OperationPolicy(id=1), Seat(id=1, seat_number="A-01", grid_row=1, grid_col=1)]
    )
    db_session.flush()
    db_session.add(
        Reservation(
            user_id=other.id,
            seat_id=1,
            start_at=at(10),
            end_at=at(11),
            status=ReservationStatus.CHECKED_IN,
        )
    )
    db_session.commit()
    clock.advance(hours=1, minutes=15)
    params = {"start_at": at(10).isoformat(), "end_at": at(11).isoformat()}
    response = client.get("/api/seats", params=params)
    assert response.status_code == 200
    assert response.json()["seats"][0]["status"] == "IN_USE"

    clock.advance(minutes=45)
    response = client.get("/api/seats", params=params)
    assert response.status_code == 400
    assert response.json()["code"] == "OUT_OF_BOOKING_WINDOW"


def test_us04_final_day_can_close_at_midnight(client, db_session):
    me = setup_student(db_session, "me")
    app.dependency_overrides[require_student] = lambda: me
    db_session.add(OperationPolicy(id=1, close_hour=24))
    db_session.commit()

    response = client.get(
        "/api/seats",
        params={"start_at": "2026-11-27T23:00:00", "end_at": "2026-11-28T00:00:00"},
    )
    assert response.status_code == 200
    assert response.json()["date"] == "2026-11-27"
    response = client.get(
        "/api/seats",
        params={"start_at": "2026-11-27T23:00:00", "end_at": "2026-11-28T01:00:00"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_TIME_RANGE"


@pytest.mark.parametrize("slot_minutes", [None, 0, -60, 840])
def test_us04_unavailable_policy_does_not_write_or_crash(client, db_session, slot_minutes):
    me = setup_student(db_session, "me")
    app.dependency_overrides[require_student] = lambda: me
    if slot_minutes is not None:
        db_session.add(OperationPolicy(id=1, slot_minutes=slot_minutes))
    db_session.commit()

    params = {"start_at": at(10).isoformat(), "end_at": at(11).isoformat()}
    response = client.get("/api/seats", params=params)
    assert response.status_code == 503
    assert response.json()["code"] == "OPERATION_POLICY_UNAVAILABLE"
    policy = db_session.get(OperationPolicy, 1)
    assert (policy.slot_minutes if policy else None) == slot_minutes
