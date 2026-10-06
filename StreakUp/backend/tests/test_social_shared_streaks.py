from datetime import date, timedelta

import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy import text

from app import create_app
from app.extensions import db
from app.models.checkin import CheckIn
from app.models.habit import Category, Habit
from app.models.social import SharedStreakGroup, SharedStreakMembership
from app.models.user import User
from app.models.user_habit import UserHabit
from app.services.social_service import (
    MAX_PARTICIPANTS,
    SocialPermissionError,
    create_group,
    get_group_detail,
    join_group,
    leave_group,
    list_groups,
)


@pytest.fixture
def app():
    instance = create_app()
    instance.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with instance.app_context():
        db.create_all()
        yield instance
        db.session.remove()
        db.drop_all()


@pytest.fixture
def seeded(app):
    with app.app_context():
        category = Category(nombre="Social")
        db.session.add(category)
        db.session.flush()

        habit = Habit(
            categoria_id=category.id,
            nombre="Privado",
            dificultad="facil",
            xp_base=10,
        )
        db.session.add(habit)
        db.session.flush()

        users = []
        user_habits = []
        today = date.today()
        for index in range(4):
            user = User(username=f"user{index}", email=f"user{index}@test.com")
            user.set_password("password")
            db.session.add(user)
            db.session.flush()
            users.append(user)

            user_habit = UserHabit(
                usuario_id=user.id,
                habito_id=habit.id,
                fecha_inicio=today - timedelta(days=10),
                activo=True,
            )
            db.session.add(user_habit)
            db.session.flush()
            user_habits.append(user_habit)

        db.session.commit()
        return {
            "habit_id": habit.id,
            "users": [user.id for user in users],
            "user_habits": [user_habit.id for user_habit in user_habits],
        }


def _add_checkin(user_habit_id: int, day: date):
    db.session.add(CheckIn(habitousuario_id=user_habit_id, fecha=day, completado=True, xp_ganado=10))
    db.session.commit()


def _force_group_start(group_id: int, start: date) -> None:
    """Backdoor for tests: move a group's start_date to a past date."""
    group = db.session.get(SharedStreakGroup, group_id)
    assert group is not None
    group.start_date = start
    if group.duration_days is not None:
        group.end_date = start + timedelta(days=group.duration_days - 1)
    db.session.commit()


def _member_status(group_id: int, user_id: int) -> str:
    m = SharedStreakMembership.query.filter_by(group_id=group_id, user_id=user_id).one()
    return m.status


def _auth_headers(user_id: int) -> dict[str, str]:
    token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Existing tests (updated for habit binding + duel fields)
# ---------------------------------------------------------------------------

def test_create_group_creates_owner_membership(app, seeded):
    with app.app_context():
        owner_id = seeded["users"][0]
        owner_habit_id = seeded["user_habits"][0]
        group = create_group(owner_id, "Equipo privado", user_habit_id=owner_habit_id)

    assert group["name"] == "Equipo privado"
    assert group["member_count"] == 1
    assert group["shared_streak"]["ready"] is False
    assert group["members"][0]["user_id"] == owner_id
    assert "@" not in str(group)
    assert group["habit_id"] == seeded["habit_id"]
    assert group["max_participants"] == MAX_PARTICIPANTS
    assert group["group_status"] == "active"
    assert group["winner_user_id"] is None
    assert group["start_date"] is not None
    assert group["duration_days"] is None


def test_create_group_with_fixed_duration_sets_end_date(app, seeded):
    with app.app_context():
        owner_id = seeded["users"][0]
        owner_habit_id = seeded["user_habits"][0]
        group = create_group(
            owner_id, "Reto Semanal", user_habit_id=owner_habit_id, duration_days=7
        )

    today = date.today()
    expected_end = (today + timedelta(days=6)).isoformat()
    assert group["duration_days"] == 7
    assert group["end_date"] == expected_end
    assert group["group_status"] == "active"


def test_create_group_rejects_non_positive_duration(app, seeded):
    with app.app_context():
        owner_id = seeded["users"][0]
        owner_habit_id = seeded["user_habits"][0]
        with pytest.raises(ValueError, match="positive"):
            create_group(owner_id, "Bad", user_habit_id=owner_habit_id, duration_days=0)
        with pytest.raises(ValueError, match="positive"):
            create_group(owner_id, "Bad", user_habit_id=owner_habit_id, duration_days=-3)


def test_join_by_invite_is_idempotent_and_reactivates(app, seeded):
    with app.app_context():
        owner_id, member_id = seeded["users"][:2]
        owner_habit_id = seeded["user_habits"][0]
        group = create_group(owner_id, "Equipo privado", user_habit_id=owner_habit_id)
        joined = join_group(member_id, group["invite_code"])
        left = leave_group(member_id, group["id"])
        rejoined = join_group(member_id, group["invite_code"])

    assert joined["member_count"] == 2
    assert left == {"left": True, "group_id": group["id"]}
    assert rejoined["member_count"] == 2
    assert sorted(member["user_id"] for member in rejoined["members"]) == sorted([owner_id, member_id])


def test_non_member_cannot_read_group_detail(app, seeded):
    with app.app_context():
        owner_id = seeded["users"][0]
        outsider_id = seeded["users"][2]
        owner_habit_id = seeded["user_habits"][0]
        group = create_group(owner_id, "Equipo privado", user_habit_id=owner_habit_id)

        with pytest.raises(SocialPermissionError):
            get_group_detail(outsider_id, group["id"])


def test_shared_streak_counts_consecutive_all_member_days_and_resets(app, seeded):
    with app.app_context():
        owner_id, member_id = seeded["users"][:2]
        owner_habit, member_habit = seeded["user_habits"][:2]
        today = date.today()
        # Start 2 days ago — checkins cover every day since start
        group = create_group(owner_id, "Equipo privado", user_habit_id=owner_habit)
        _force_group_start(group["id"], today - timedelta(days=2))
        join_group(member_id, group["invite_code"])

        for offset in (2, 1, 0):
            _add_checkin(owner_habit, today - timedelta(days=offset))
            _add_checkin(member_habit, today - timedelta(days=offset))

        detail = get_group_detail(owner_id, group["id"])
        assert detail["shared_streak"]["current"] == 3
        assert detail["shared_streak"]["today_completed_members"] == 2

        # Removing member's yesterday checkin marks them lost → owner wins → group ends
        db.session.delete(
            CheckIn.query.filter_by(
                habitousuario_id=member_habit, fecha=today - timedelta(days=1)
            ).one()
        )
        db.session.commit()

        reset_detail = get_group_detail(owner_id, group["id"])
        assert reset_detail["group_status"] == "finished"
        assert reset_detail["shared_streak"]["current"] == 0


def test_group_detail_omits_email_and_exposes_habit_name(app, seeded):
    with app.app_context():
        owner_id, member_id = seeded["users"][:2]
        owner_habit_id = seeded["user_habits"][0]
        group = create_group(owner_id, "Equipo privado", user_habit_id=owner_habit_id)
        detail = join_group(member_id, group["invite_code"])

    serialized = str(detail)
    assert "email" not in serialized
    assert "@test.com" not in serialized
    assert detail["habit_name"] == "Privado"
    assert "members" in detail


def test_groups_route_returns_200_when_user_has_no_groups(app):
    with app.app_context():
        user = User(username="solo", email="solo@test.com")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        headers = _auth_headers(user.id)

    response = app.test_client().get("/api/social/groups", headers=headers)

    assert response.status_code == 200
    assert response.get_json() == []


def test_groups_route_returns_200_with_active_group_and_no_checkins(app, seeded):
    with app.app_context():
        owner_id, member_id = seeded["users"][:2]
        owner_habit_id = seeded["user_habits"][0]
        group = create_group(owner_id, "Sin checkins", user_habit_id=owner_habit_id)
        join_group(member_id, group["invite_code"])
        headers = _auth_headers(owner_id)

    response = app.test_client().get("/api/social/groups", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert any(item["id"] == group["id"] for item in payload)
    listed = next(item for item in payload if item["id"] == group["id"])
    assert listed["member_count"] == 2
    assert listed["shared_streak"]["today_completed_members"] == 0


def test_group_detail_route_tolerates_member_without_user_relation(app, seeded):
    with app.app_context():
        owner_id = seeded["users"][0]
        owner_habit_id = seeded["user_habits"][0]
        group = create_group(owner_id, "Legacy member", user_habit_id=owner_habit_id)
        missing_user_id = 999999
        db.session.execute(text("PRAGMA foreign_keys=OFF"))
        db.session.add(
            SharedStreakMembership(
                group_id=group["id"],
                user_id=missing_user_id,
                status="active",
                share_progress=True,
            )
        )
        db.session.commit()
        db.session.execute(text("PRAGMA foreign_keys=ON"))
        headers = _auth_headers(missing_user_id)

    response = app.test_client().get(
        f"/api/social/groups/{group['id']}", headers=headers
    )

    assert response.status_code == 200
    ghost_member = next(
        member for member in response.get_json()["members"]
        if member["user_id"] == missing_user_id
    )
    assert ghost_member["username"] is None


# ---------------------------------------------------------------------------
# Phase 1 tests (unchanged)
# ---------------------------------------------------------------------------

def test_create_group_requires_user_habit_id(app, seeded):
    with app.app_context():
        owner_id = seeded["users"][0]
        with pytest.raises(ValueError, match="user_habit_id is required"):
            create_group(owner_id, "Sin hábito")


def test_create_group_rejects_habit_belonging_to_other_user(app, seeded):
    with app.app_context():
        other_user_id = seeded["users"][1]
        owners_habit_id = seeded["user_habits"][0]
        with pytest.raises(SocialPermissionError):
            create_group(other_user_id, "Ajeno", user_habit_id=owners_habit_id)


def test_join_fourth_member_is_rejected(app, seeded):
    with app.app_context():
        users = seeded["users"]
        habits = seeded["user_habits"]
        group = create_group(users[0], "Lleno", user_habit_id=habits[0])
        join_group(users[1], group["invite_code"])
        join_group(users[2], group["invite_code"])
        with pytest.raises(ValueError, match="máximo"):
            join_group(users[3], group["invite_code"])


def test_rejoining_after_leave_does_not_count_as_new_slot(app, seeded):
    """Member who left and rejoins must not be blocked by their own vacated slot."""
    with app.app_context():
        users = seeded["users"]
        habits = seeded["user_habits"]
        group = create_group(users[0], "Reactivar", user_habit_id=habits[0])
        join_group(users[1], group["invite_code"])
        join_group(users[2], group["invite_code"])
        leave_group(users[1], group["id"])
        rejoined = join_group(users[1], group["invite_code"])
        assert rejoined["member_count"] == 3


def test_join_auto_creates_user_habit_when_absent(app, seeded):
    """Joining a habit-bound group auto-creates UserHabit for members who don't have it."""
    with app.app_context():
        category = Category(nombre="Extra")
        db.session.add(category)
        db.session.flush()
        catalog_habit = Habit(
            categoria_id=category.id,
            nombre="NuevoHábito",
            dificultad="facil",
            xp_base=5,
        )
        db.session.add(catalog_habit)
        db.session.flush()

        owner_id = seeded["users"][0]
        owner_habit = UserHabit(
            usuario_id=owner_id,
            habito_id=catalog_habit.id,
            fecha_inicio=date.today(),
            activo=True,
        )
        db.session.add(owner_habit)
        db.session.flush()
        db.session.commit()

        group = create_group(owner_id, "Auto-create", user_habit_id=owner_habit.id)

        member_id = seeded["users"][1]
        pre_count = UserHabit.query.filter_by(
            usuario_id=member_id, habito_id=catalog_habit.id
        ).count()
        assert pre_count == 0

        join_group(member_id, group["invite_code"])

        post_count = UserHabit.query.filter_by(
            usuario_id=member_id, habito_id=catalog_habit.id, activo=True
        ).count()
        assert post_count == 1


def test_shared_streak_only_counts_bound_habit_checkins(app, seeded):
    """Progress on a different habit must not inflate the shared streak."""
    with app.app_context():
        category = Category(nombre="Extra2")
        db.session.add(category)
        db.session.flush()
        other_habit = Habit(
            categoria_id=category.id,
            nombre="OtroHábito",
            dificultad="facil",
            xp_base=5,
        )
        db.session.add(other_habit)
        db.session.flush()

        users = seeded["users"]
        bound_habits = seeded["user_habits"]
        today = date.today()

        other_uh_owner = UserHabit(
            usuario_id=users[0], habito_id=other_habit.id,
            fecha_inicio=today, activo=True,
        )
        other_uh_member = UserHabit(
            usuario_id=users[1], habito_id=other_habit.id,
            fecha_inicio=today, activo=True,
        )
        db.session.add_all([other_uh_owner, other_uh_member])
        db.session.flush()
        db.session.commit()

        group = create_group(users[0], "Filtrado", user_habit_id=bound_habits[0])
        join_group(users[1], group["invite_code"])

        _add_checkin(other_uh_owner.id, today)
        _add_checkin(other_uh_member.id, today)

        detail = get_group_detail(users[0], group["id"])
        assert detail["shared_streak"]["today_completed_members"] == 0
        assert detail["shared_streak"]["current"] == 0

        _add_checkin(bound_habits[0], today)
        _add_checkin(bound_habits[1], today)

        detail2 = get_group_detail(users[0], group["id"])
        assert detail2["shared_streak"]["today_completed_members"] == 2
        assert detail2["shared_streak"]["current"] == 1


def test_group_payload_includes_habit_id_and_max_participants(app, seeded):
    with app.app_context():
        owner_id = seeded["users"][0]
        owner_habit_id = seeded["user_habits"][0]
        group = create_group(owner_id, "Payload test", user_habit_id=owner_habit_id)

    assert group["habit_id"] == seeded["habit_id"]
    assert group["max_participants"] == MAX_PARTICIPANTS


# ---------------------------------------------------------------------------
# Phase 3 — Duel outcome tests
# ---------------------------------------------------------------------------

def test_member_who_misses_habit_is_marked_lost(app, seeded):
    """A member who doesn't validate the bound habit for a past day is marked lost."""
    with app.app_context():
        owner_id, member_id = seeded["users"][:2]
        owner_habit, member_habit = seeded["user_habits"][:2]
        today = date.today()
        yesterday = today - timedelta(days=1)

        group = create_group(owner_id, "Duel basic", user_habit_id=owner_habit)
        _force_group_start(group["id"], yesterday)
        join_group(member_id, group["invite_code"])

        # Owner validates yesterday; member does NOT
        _add_checkin(owner_habit, yesterday)

        detail = get_group_detail(owner_id, group["id"])
        member_entry = next(m for m in detail["members"] if m["user_id"] == member_id)
        owner_entry = next(m for m in detail["members"] if m["user_id"] == owner_id)

    assert member_entry["status"] == "lost"
    assert owner_entry["status"] in ("active", "winner")
    assert member_entry["lost_at"] is not None


def test_member_who_validates_stays_active(app, seeded):
    """A member who validates on every past day remains active."""
    with app.app_context():
        owner_id, member_id = seeded["users"][:2]
        owner_habit, member_habit = seeded["user_habits"][:2]
        today = date.today()
        yesterday = today - timedelta(days=1)

        group = create_group(owner_id, "Duel validate", user_habit_id=owner_habit)
        _force_group_start(group["id"], yesterday)
        join_group(member_id, group["invite_code"])

        _add_checkin(owner_habit, yesterday)
        _add_checkin(member_habit, yesterday)

        detail = get_group_detail(owner_id, group["id"])
        for member in detail["members"]:
            assert member["status"] == "active"


def test_checkin_on_different_habit_does_not_prevent_lost(app, seeded):
    """Completing a DIFFERENT habit does not save a member from being marked lost."""
    with app.app_context():
        category = Category(nombre="Other")
        db.session.add(category)
        db.session.flush()
        other_cat_habit = Habit(
            categoria_id=category.id, nombre="Otro", dificultad="facil", xp_base=5
        )
        db.session.add(other_cat_habit)
        db.session.flush()

        owner_id, member_id = seeded["users"][:2]
        owner_habit = seeded["user_habits"][0]
        today = date.today()
        yesterday = today - timedelta(days=1)

        other_uh = UserHabit(
            usuario_id=member_id, habito_id=other_cat_habit.id,
            fecha_inicio=today - timedelta(days=5), activo=True,
        )
        db.session.add(other_uh)
        db.session.flush()
        db.session.commit()

        group = create_group(owner_id, "Wrong habit", user_habit_id=owner_habit)
        _force_group_start(group["id"], yesterday)
        join_group(member_id, group["invite_code"])

        _add_checkin(owner_habit, yesterday)
        # Member checks in on the OTHER habit — should still be lost
        _add_checkin(other_uh.id, yesterday)

        detail = get_group_detail(owner_id, group["id"])
        member_entry = next(m for m in detail["members"] if m["user_id"] == member_id)

    assert member_entry["status"] == "lost"


def test_unlimited_group_ends_when_one_active_remains(app, seeded):
    """In unlimited mode, the last active member becomes the winner and group closes."""
    with app.app_context():
        owner_id, member_id = seeded["users"][:2]
        owner_habit, member_habit = seeded["user_habits"][:2]
        today = date.today()
        yesterday = today - timedelta(days=1)

        group = create_group(owner_id, "Unlimited duel", user_habit_id=owner_habit)
        _force_group_start(group["id"], yesterday)
        join_group(member_id, group["invite_code"])

        # Owner validates; member misses → member goes lost → owner is last active
        _add_checkin(owner_habit, yesterday)

        detail = get_group_detail(owner_id, group["id"])
        owner_entry = next(m for m in detail["members"] if m["user_id"] == owner_id)
        member_entry = next(m for m in detail["members"] if m["user_id"] == member_id)
        group_id = group["id"]

    assert detail["group_status"] == "finished"
    assert owner_entry["status"] == "winner"
    assert member_entry["status"] == "lost"
    assert detail["winner_user_id"] == owner_id


def test_unlimited_all_lost_closes_group_without_winner(app, seeded):
    """If everyone misses the same day in unlimited mode, group closes with no winner."""
    with app.app_context():
        owner_id, member_id = seeded["users"][:2]
        owner_habit = seeded["user_habits"][0]
        today = date.today()
        yesterday = today - timedelta(days=1)

        group = create_group(owner_id, "No winner", user_habit_id=owner_habit)
        _force_group_start(group["id"], yesterday)
        join_group(member_id, group["invite_code"])

        # Neither validates yesterday
        detail = get_group_detail(owner_id, group["id"])

    assert detail["group_status"] == "finished"
    assert detail["winner_user_id"] is None
    for member in detail["members"]:
        assert member["status"] == "lost"


def test_fixed_duration_group_ends_after_duration_days(app, seeded):
    """A fixed-duration group finalizes after the challenge period ends."""
    with app.app_context():
        owner_id, member_id = seeded["users"][:2]
        owner_habit, member_habit = seeded["user_habits"][:2]
        today = date.today()

        # 3-day challenge that started 3 days ago (end_date = yesterday + 1 day ago)
        group = create_group(
            owner_id, "Fixed 3d", user_habit_id=owner_habit, duration_days=3
        )
        start = today - timedelta(days=3)
        _force_group_start(group["id"], start)
        join_group(member_id, group["invite_code"])

        # Both complete all 3 days of the challenge (3 days ago, 2 days ago, 1 day ago)
        for offset in (3, 2, 1):
            _add_checkin(owner_habit, today - timedelta(days=offset))
            _add_checkin(member_habit, today - timedelta(days=offset))

        detail = get_group_detail(owner_id, group["id"])

    assert detail["group_status"] == "finished"


def test_winner_is_member_with_most_completed_days(app, seeded):
    """In fixed-duration mode, the member with more completed days wins."""
    with app.app_context():
        owner_id, member_id = seeded["users"][:2]
        owner_habit, member_habit = seeded["user_habits"][:2]
        today = date.today()

        # 3-day challenge
        group = create_group(
            owner_id, "Best score", user_habit_id=owner_habit, duration_days=3
        )
        start = today - timedelta(days=3)
        _force_group_start(group["id"], start)
        join_group(member_id, group["invite_code"])

        # Owner completes 3/3; member completes 2/3 (misses day 1)
        for offset in (3, 2, 1):
            _add_checkin(owner_habit, today - timedelta(days=offset))
        for offset in (2, 1):
            _add_checkin(member_habit, today - timedelta(days=offset))

        detail = get_group_detail(owner_id, group["id"])
        owner_entry = next(m for m in detail["members"] if m["user_id"] == owner_id)
        member_entry = next(m for m in detail["members"] if m["user_id"] == member_id)

    assert detail["group_status"] == "finished"
    assert owner_entry["status"] == "winner"
    assert member_entry["status"] != "winner"
    assert detail["winner_user_id"] == owner_id
    assert owner_entry["completed_days"] == 3
    assert member_entry["completed_days"] == 2


def test_fixed_duration_tie_crowns_all_tied_members(app, seeded):
    """In a fixed-duration tie, all tied members become winners and winner_user_id is null."""
    with app.app_context():
        owner_id, member_id = seeded["users"][:2]
        owner_habit, member_habit = seeded["user_habits"][:2]
        today = date.today()

        group = create_group(
            owner_id, "Tie game", user_habit_id=owner_habit, duration_days=2
        )
        start = today - timedelta(days=2)
        _force_group_start(group["id"], start)
        join_group(member_id, group["invite_code"])

        # Both complete same days
        for offset in (2, 1):
            _add_checkin(owner_habit, today - timedelta(days=offset))
            _add_checkin(member_habit, today - timedelta(days=offset))

        detail = get_group_detail(owner_id, group["id"])
        for member in detail["members"]:
            assert member["status"] == "winner"

    assert detail["group_status"] == "finished"
    assert detail["winner_user_id"] is None


def test_left_status_is_not_treated_as_lost(app, seeded):
    """A member who voluntarily leaves retains 'left' status, not 'lost'."""
    with app.app_context():
        owner_id, member_id = seeded["users"][:2]
        owner_habit = seeded["user_habits"][0]
        today = date.today()
        yesterday = today - timedelta(days=1)

        group = create_group(owner_id, "Leave test", user_habit_id=owner_habit)
        _force_group_start(group["id"], yesterday)
        join_group(member_id, group["invite_code"])
        leave_group(member_id, group["id"])

        # Trigger evaluation
        get_group_detail(owner_id, group["id"])

        membership = SharedStreakMembership.query.filter_by(
            group_id=group["id"], user_id=member_id
        ).one()

    assert membership.status == "left"


def test_lost_member_cannot_rejoin(app, seeded):
    """A member who was marked lost cannot rejoin the group."""
    with app.app_context():
        owner_id, member_id = seeded["users"][:2]
        owner_habit = seeded["user_habits"][0]
        today = date.today()
        yesterday = today - timedelta(days=1)

        group = create_group(owner_id, "No rejoin", user_habit_id=owner_habit)
        _force_group_start(group["id"], yesterday)
        join_group(member_id, group["invite_code"])

        # Owner validates, member doesn't → member becomes lost
        _add_checkin(owner_habit, yesterday)
        get_group_detail(owner_id, group["id"])  # triggers evaluation

        with pytest.raises(ValueError, match="perder"):
            join_group(member_id, group["invite_code"])


def test_streak_starts_from_group_start_date_not_historical_checkins(app, seeded):
    """Historical check-ins before start_date do not count toward the shared streak."""
    with app.app_context():
        owner_id, member_id = seeded["users"][:2]
        owner_habit, member_habit = seeded["user_habits"][:2]
        today = date.today()

        group = create_group(owner_id, "Streak bound", user_habit_id=owner_habit)
        # Start 2 days ago so checkins from before don't count
        _force_group_start(group["id"], today - timedelta(days=2))
        join_group(member_id, group["invite_code"])

        # Historical checkins: 7 and 5 days ago (before start_date)
        for offset in (7, 5):
            _add_checkin(owner_habit, today - timedelta(days=offset))
            _add_checkin(member_habit, today - timedelta(days=offset))

        # Challenge checkins: 2 days ago, 1 day ago, today
        for offset in (2, 1, 0):
            _add_checkin(owner_habit, today - timedelta(days=offset))
            _add_checkin(member_habit, today - timedelta(days=offset))

        detail = get_group_detail(owner_id, group["id"])

    # Streak should be 3 (start_date to today), not 5+ (historical)
    assert detail["shared_streak"]["current"] == 3


def test_list_groups_shows_lost_and_winner_memberships(app, seeded):
    """list_groups includes groups where the user is lost or winner."""
    with app.app_context():
        owner_id, member_id = seeded["users"][:2]
        owner_habit, member_habit = seeded["user_habits"][:2]
        today = date.today()
        yesterday = today - timedelta(days=1)

        group = create_group(owner_id, "List test", user_habit_id=owner_habit)
        _force_group_start(group["id"], yesterday)
        join_group(member_id, group["invite_code"])

        # Owner validates; member doesn't → member lost, owner wins
        _add_checkin(owner_habit, yesterday)

        # Force evaluation
        get_group_detail(owner_id, group["id"])

        # Both should still see the group in their list
        owner_groups = list_groups(owner_id)
        member_groups = list_groups(member_id)

    assert any(g["id"] == group["id"] for g in owner_groups)
    assert any(g["id"] == group["id"] for g in member_groups)


def test_leave_group_does_not_delete_user_habit(app, seeded):
    """Leaving a shared streak group must not affect the user's habit."""
    with app.app_context():
        owner_id, member_id = seeded["users"][:2]
        owner_habit_id = seeded["user_habits"][0]
        member_habit_id = seeded["user_habits"][1]

        group = create_group(owner_id, "Leave habit", user_habit_id=owner_habit_id)
        join_group(member_id, group["invite_code"])
        leave_group(member_id, group["id"])

        uh = db.session.get(UserHabit, member_habit_id)

    assert uh is not None
    assert uh.activo is True
