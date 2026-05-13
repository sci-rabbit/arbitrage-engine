import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from repositrories.user_repository import UserRepository
from tests.factories import make_user

# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------

async def test_get_returns_user(db: AsyncSession):
    user = await make_user(db, email="a@test.com")
    result = await UserRepository(db).get(user.id)
    assert result is not None
    assert result.id == user.id


async def test_get_returns_none_for_missing_id(db: AsyncSession):
    result = await UserRepository(db).get(999_999)
    assert result is None


# ---------------------------------------------------------------------------
# get_one_by
# ---------------------------------------------------------------------------

async def test_get_one_by_email(db: AsyncSession):
    user = await make_user(db, email="b@test.com")
    result = await UserRepository(db).get_one_by(email="b@test.com")
    assert result is not None
    assert result.id == user.id


async def test_get_one_by_returns_none_when_not_found(db: AsyncSession):
    result = await UserRepository(db).get_one_by(email="nobody@test.com")
    assert result is None


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

async def test_create_persists_user(db: AsyncSession):
    repo = UserRepository(db)
    user = await repo.create(
        email="c@test.com",
        password="hashed",
        username="cuser",
    )
    assert user.id is not None
    fetched = await repo.get(user.id)
    assert fetched.email == "c@test.com"


async def test_create_applies_defaults(db: AsyncSession):
    user = await UserRepository(db).create(email="d@test.com", password="x")
    assert user.is_admin is False
    assert user.is_active is True
    assert user.has_access is False
    assert user.orders_count == 0


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

async def test_update_changes_fields(db: AsyncSession):
    repo = UserRepository(db)
    user = await make_user(db, email="e@test.com", has_access=False)
    updated = await repo.update(user, {"has_access": True, "first_name": "Alice"})
    assert updated.has_access is True
    assert updated.first_name == "Alice"


async def test_update_is_persisted(db: AsyncSession):
    repo = UserRepository(db)
    user = await make_user(db, email="f@test.com")
    await repo.update(user, {"first_name": "Bob"})
    fetched = await repo.get(user.id)
    assert fetched.first_name == "Bob"


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

async def test_delete_removes_user(db: AsyncSession):
    repo = UserRepository(db)
    user = await make_user(db, email="g@test.com")
    user_id = user.id
    await repo.delete(user)
    await db.flush()
    assert await repo.get(user_id) is None


# ---------------------------------------------------------------------------
# list / list_by / paginate
# ---------------------------------------------------------------------------

async def test_list_returns_all_users(db: AsyncSession):
    await make_user(db, email="h1@test.com", username="h1")
    await make_user(db, email="h2@test.com", username="h2")
    users = await UserRepository(db).list(limit=100)
    emails = {u.email for u in users}
    assert {"h1@test.com", "h2@test.com"}.issubset(emails)


async def test_list_by_filters_correctly(db: AsyncSession):
    await make_user(db, email="i1@test.com", username="i1", has_access=True)
    await make_user(db, email="i2@test.com", username="i2", has_access=False)
    result = await UserRepository(db).list_by(has_access=True)
    assert all(u.has_access for u in result)
    assert any(u.email == "i1@test.com" for u in result)


async def test_paginate_respects_limit_and_offset(db: AsyncSession):
    for i in range(5):
        await make_user(db, email=f"p{i}@test.com", username=f"puser{i}")

    page1 = await UserRepository(db).paginate(limit=2, offset=0)
    page2 = await UserRepository(db).paginate(limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2
    assert {u.id for u in page1}.isdisjoint({u.id for u in page2})


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

async def test_search_by_email_partial(db: AsyncSession):
    await make_user(db, email="unique_xyz@test.com", username="srch1")
    results = await UserRepository(db).search("unique_xyz")
    assert any(u.email == "unique_xyz@test.com" for u in results)


async def test_search_by_username_partial(db: AsyncSession):
    await make_user(db, email="srch2@test.com", username="findme_abc")
    results = await UserRepository(db).search("findme_abc")
    assert any(u.username == "findme_abc" for u in results)


async def test_search_case_insensitive(db: AsyncSession):
    await make_user(db, email="upper@test.com", username="upperuser")
    results = await UserRepository(db).search("UPPER@TEST")
    assert any(u.email == "upper@test.com" for u in results)


async def test_search_returns_empty_when_no_match(db: AsyncSession):
    results = await UserRepository(db).search("zzz_no_match_zzz")
    assert results == []


# ---------------------------------------------------------------------------
# get_for_update — пропускаем, SQLite не поддерживает FOR UPDATE
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="WITH FOR UPDATE not supported by SQLite")
async def test_get_for_update(db: AsyncSession):
    user = await make_user(db, email="lock@test.com")
    result = await UserRepository(db).get_for_update(user.id)
    assert result.id == user.id
