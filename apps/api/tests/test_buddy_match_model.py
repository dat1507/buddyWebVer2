"""BUDDY-001 model, canonical pair, constraints, and index contracts."""

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Enum, ForeignKeyConstraint, Table, UniqueConstraint, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateIndex, CreateTable

from app.models import (
    BuddyMatch,
    MatchStatus,
    canonical_user_pair,
)


def test_canonical_user_pair_is_symmetric_deterministic_and_rejects_self() -> None:
    lower = UUID("10000000-0000-4000-8000-000000000001")
    higher = UUID("f0000000-0000-4000-8000-000000000001")

    assert canonical_user_pair(lower, higher) == (lower, higher)
    assert canonical_user_pair(higher, lower) == (lower, higher)
    with pytest.raises(ValueError, match="distinct users"):
        canonical_user_pair(lower, lower)


def test_match_is_active_only_and_has_no_speculative_lifecycle_or_version() -> None:
    assert tuple(MatchStatus) == (MatchStatus.ACTIVE,)
    table = cast(Table, BuddyMatch.__table__)
    status_type = cast(Enum, table.c.status.type)

    assert status_type.name == "match_status"
    assert status_type.enums == [MatchStatus.ACTIVE.value]
    assert inspect(BuddyMatch).version_id_col is None
    for speculative_column in (
        "ended_at",
        "cancelled_at",
        "archived_at",
        "version",
    ):
        assert speculative_column not in table.c
    assert table.c.semester_id.nullable is False


def test_match_model_persists_participants_provenance_and_safe_score_snapshot() -> None:
    activated_at = datetime(2026, 9, 30, 1, 0, tzinfo=UTC)
    buddy_match = BuddyMatch(
        participant_one_user_id=uuid4(),
        participant_two_user_id=uuid4(),
        participant_one_profile_id=uuid4(),
        participant_two_profile_id=uuid4(),
        accepted_invitation_id=uuid4(),
        semester_id=uuid4(),
        status=MatchStatus.ACTIVE,
        score=75,
        score_breakdown={
            "reference_week_start": "2026-09-28",
            "interests": {"similarity": 1, "weight": 40, "points": 40},
        },
        activated_at=activated_at,
        created_at=activated_at,
        updated_at=activated_at,
    )

    assert buddy_match.status is MatchStatus.ACTIVE
    assert buddy_match.score == 75
    assert buddy_match.activated_at == activated_at
    assert "email" not in repr(buddy_match.score_breakdown).lower()


def test_postgresql_ddl_enforces_active_unordered_pair_and_query_indexes() -> None:
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    table = cast(Table, BuddyMatch.__table__)
    table_ddl = str(CreateTable(table).compile(dialect=dialect)).lower()
    index_ddl = {
        str(index.name): str(CreateIndex(index).compile(dialect=dialect)).lower()
        for index in table.indexes
    }
    foreign_keys = {
        str(constraint.name): constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    unique_constraints = {
        str(constraint.name): constraint
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert table.schema == "app_private"
    assert "generated always as (least(participant_one_user_id" in table_ddl
    assert "generated always as (greatest(participant_one_user_id" in table_ddl
    assert "participant_one_user_id <> participant_two_user_id" in table_ddl
    assert "participant_one_profile_id <> participant_two_profile_id" in table_ddl
    assert "score between 0 and 100" in table_ddl
    assert "jsonb_typeof(score_breakdown) = 'object'" in table_ddl
    assert "where status = 'active'" in index_ddl["uq_matches_active_pair"]
    assert "unique" in index_ddl["uq_matches_active_pair"]
    assert index_ddl["ix_matches_participant_one_status_activated_at"]
    assert index_ddl["ix_matches_participant_two_status_activated_at"]
    assert not any(
        index.unique
        for index in table.indexes
        if index.name
        in {
            "ix_matches_participant_one_status_activated_at",
            "ix_matches_participant_two_status_activated_at",
        }
    )
    assert set(index_ddl) == {
        "uq_matches_active_pair",
        "ix_matches_participant_one_status_activated_at",
        "ix_matches_participant_two_status_activated_at",
        "ix_matches_participant_one_profile_id",
        "ix_matches_participant_two_profile_id",
        "ix_matches_semester_id",
    }
    assert set(foreign_keys) == {
        "fk_matches_participant_one_user_id_users",
        "fk_matches_participant_two_user_id_users",
        "fk_matches_participant_one_profile_id_student_profiles",
        "fk_matches_participant_two_profile_id_student_profiles",
        "fk_matches_accepted_invitation_id_matching_invitations",
        "fk_matches_semester_id_semesters",
    }
    assert all(
        constraint.ondelete == "CASCADE"
        for name, constraint in foreign_keys.items()
        if name != "fk_matches_semester_id_semesters"
    )
    assert foreign_keys["fk_matches_semester_id_semesters"].ondelete == "RESTRICT"
    assert "uq_matches_accepted_invitation_id" in unique_constraints
