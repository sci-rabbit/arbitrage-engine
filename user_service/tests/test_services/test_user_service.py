import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import verify_password
from dto.user_dto import CreateUserDTO, UpdateUserDTO
from exceptions.user import UserAlreadyExists, UserNotFound
from services.user.user_service import UserService
from tests.factories import make_user


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

async def test_create_returns_user_with_correct_email(db: AsyncSession):
    user = await UserService(db).create(CreateUserDTO(email="new@test.com", password="secret"))
    assert user.email == "new@test.com"


async def test_create_hashes_password(db: AsyncSession):
    user = await UserService(db).create(CreateUserDTO(email="hash@test.com", password="plaintext"))
    assert user.password != "plaintext"
    assert verify_password("plaintext", user.password)


async def test_create_raises_if_email_already_exists(db: AsyncSession):
    await make_user(db, email="dup@test.com")
    with pytest.raises(UserAlreadyExists):
        await UserService(db).create(CreateUserDTO(email="dup@test.com", password="x"))


async def test_create_persists_to_db(db: AsyncSession):
    user = await UserService(db).create(CreateUserDTO(email="persist@test.com", password="x"))
    assert user.id is not None
    fetched = await UserService(db).get_by_id(user.id)
    assert fetched.email == "persist@test.com"


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------

async def test_get_by_id_returns_correct_user(db: AsyncSession):
    user = await make_user(db, email="byid@test.com")
    result = await UserService(db).get_by_id(user.id)
    assert result.id == user.id


async def test_get_by_id_raises_if_not_found(db: AsyncSession):
    with pytest.raises(UserNotFound):
        await UserService(db).get_by_id(999_999)


# ---------------------------------------------------------------------------
# get_by_email
# ---------------------------------------------------------------------------

async def test_get_by_email_returns_correct_user(db: AsyncSession):
    await make_user(db, email="byemail@test.com")
    result = await UserService(db).get_by_email("byemail@test.com")
    assert result.email == "byemail@test.com"


async def test_get_by_email_raises_if_not_found(db: AsyncSession):
    with pytest.raises(UserNotFound):
        await UserService(db).get_by_email("ghost@test.com")


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

async def test_update_changes_simple_fields(db: AsyncSession):
    user = await make_user(db, email="upd@test.com")
    updated = await UserService(db).update(user, UpdateUserDTO(first_name="Alice", last_name="Smith"))
    assert updated.first_name == "Alice"
    assert updated.last_name == "Smith"


async def test_update_ignores_none_fields(db: AsyncSession):
    user = await make_user(db, email="none@test.com", first_name="Original")
    updated = await UserService(db).update(user, UpdateUserDTO(first_name=None, last_name="New"))
    assert updated.first_name == "Original"


async def test_update_hashes_password_when_provided(db: AsyncSession):
    user = await make_user(db, email="updpwd@test.com", password="old")
    updated = await UserService(db).update(user, UpdateUserDTO(password="newplain"))
    assert updated.password != "newplain"
    assert verify_password("newplain", updated.password)


# ---------------------------------------------------------------------------
# set_verified
# ---------------------------------------------------------------------------

async def test_set_verified_marks_user_as_verified(db: AsyncSession):
    user = await make_user(db, email="verify@test.com", is_verified=False)
    assert user.is_verified is False
    await UserService(db).set_verified(user)
    assert user.is_verified is True


# ---------------------------------------------------------------------------
# set_password
# ---------------------------------------------------------------------------

async def test_set_password_updates_and_hashes(db: AsyncSession):
    user = await make_user(db, email="setpwd@test.com", password="old")
    await UserService(db).set_password(user, "brandnew")
    assert verify_password("brandnew", user.password)
    assert not verify_password("old", user.password)


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

async def test_delete_removes_user(db: AsyncSession):
    user = await make_user(db, email="del@test.com")
    user_id = user.id
    await UserService(db).delete(user)
    await db.flush()
    with pytest.raises(UserNotFound):
        await UserService(db).get_by_id(user_id)