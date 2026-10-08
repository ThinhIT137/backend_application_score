from fastapi import FastAPI

from src.core.exceptions import register_exception_handlers
from src.router.diem_chuan_router import router as diem_chuan_router
from src.router.diem_router import router as diem_router
from src.router.ho_so_router import router as ho_so_router

app = FastAPI(title="backend_application_score", version="0.1.0")
register_exception_handlers(app)
app.include_router(ho_so_router)
app.include_router(diem_router)
app.include_router(diem_chuan_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
