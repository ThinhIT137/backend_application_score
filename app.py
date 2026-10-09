from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.core.exceptions import register_exception_handlers
from src.router.diem_router import router as diem_router
from src.router.ho_so_router import router as ho_so_router
from src.router.admission_router import router as admission_router

app = FastAPI(title="backend_application_score", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
# Đăng ký các router
app.include_router(ho_so_router)
app.include_router(diem_router)
app.include_router(admission_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8100, reload=True)
