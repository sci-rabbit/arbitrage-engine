from sqlalchemy.ext.asyncio import AsyncSession

from services.user.admin_user_service import AdminUserService
from tests.factories import make_user


async def test_list_returns_users(db: AsyncSession):
    u1 = await make_user(db, email="au1@test.com", username="au1")
    u2 = await make_user(db, email="au2@test.com", username="au2")
    users = await AdminUserService(db).list(limit=100)
    ids = {u.id for u in users}
    assert {u1.id, u2.id}.issubset(ids)


async def test_list_filtered_by_flag(db: AsyncSession):
    await make_user(db, email="noaccess@test.com", username="noaccess", has_access=False)
    await make_user(db, email="access@test.com", username="access", has_access=True)
    result = await AdminUserService(db).list(limit=100, has_access=True)
    assert all(u.has_access for u in result)
    assert any(u.email == "access@test.com" for u in result)


async def test_search_by_email(db: AsyncSession):
    await make_user(db, email="findme_admin@test.com", username="fma")
    results = await AdminUserService(db).search("findme_admin")
    assert any(u.email == "findme_admin@test.com" for u in results)


async def test_search_returns_empty_on_no_match(db: AsyncSession):
    results = await AdminUserService(db).search("zzz_no_match_admin")
    assert results == []


async def test_grant_access_sets_flag(db: AsyncSession):
    user = await make_user(db, email="grant@test.com", has_access=False)
    updated = await AdminUserService(db).grant_access(user)
    assert updated.has_access is True


async def test_revoke_access_clears_flag(db: AsyncSession):
    user = await make_user(db, email="revoke@test.com", has_access=True)
    updated = await AdminUserService(db).revoke_access(user)
    assert updated.has_access is False