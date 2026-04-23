from fastapi import APIRouter

from app.api.routers import (
    advising,
    attendance,
    backup,
    canvas,
    courses,
    documents,
    health,
    interactions,
    llm,
    reports,
    rubrics,
    settings,
    students,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(canvas.router)
api_router.include_router(courses.router)
api_router.include_router(students.router)
api_router.include_router(attendance.router)
api_router.include_router(advising.router)
api_router.include_router(interactions.router)
api_router.include_router(rubrics.router)
api_router.include_router(documents.router)
api_router.include_router(llm.router)
api_router.include_router(reports.router)
api_router.include_router(backup.router)
api_router.include_router(settings.router)
