from fastapi import APIRouter

from api.routes.admin.users import router as users_router
from api.routes.admin.subscriptions import router as subscriptions_router
from api.routes.admin.user_subscriptions import router as user_subscriptions_router
from api.routes.admin.transactions import router as transactions_router
from api.routes.admin.orders import router as orders_router

router = APIRouter(prefix="/admin")

router.include_router(users_router)
router.include_router(subscriptions_router)
router.include_router(user_subscriptions_router)
router.include_router(transactions_router)
router.include_router(orders_router)
