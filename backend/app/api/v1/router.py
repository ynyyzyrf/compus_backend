from fastapi import APIRouter

from app.api.v1 import (
    activity,
    admin,
    admin_ai,
    admin_activity,
    admin_articles,
    admin_photos,
    admin_relays,
    articles,
    auth,
    directory,
    photos,
    profile,
    relay,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(directory.router)
api_router.include_router(articles.router)
api_router.include_router(admin_articles.router)
api_router.include_router(profile.router)
api_router.include_router(activity.router)
api_router.include_router(admin_activity.router)
api_router.include_router(photos.router)
api_router.include_router(photos.me_router)
api_router.include_router(admin_photos.router)
api_router.include_router(admin_ai.router)
api_router.include_router(relay.router)
api_router.include_router(admin_relays.router)
api_router.include_router(admin.router)
