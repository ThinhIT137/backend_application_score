from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.core.exceptions import register_exception_handlers
from src.core.config import get_api_security_settings
from src.core.api_security import ApiSecurityMiddleware
from src.router.diem_router import router as diem_router
from src.router.ho_so_router import router as ho_so_router
from src.router.admission_router import router as admission_router
from src.router.diem_chuan_router import router as diem_chuan_router
from src.router.thong_ke_router import router as thong_ke_router
from src.router.candidate_auth_router import router as candidate_auth_router
from src.router.workflow_router import router as workflow_router

app = FastAPI(title="backend_application_score", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_api_security_settings().allowed_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ApiSecurityMiddleware)

register_exception_handlers(app)
# Đăng ký các router
app.include_router(ho_so_router)
app.include_router(diem_router)
app.include_router(admission_router)
app.include_router(diem_chuan_router)
app.include_router(thong_ke_router)
app.include_router(candidate_auth_router)
app.include_router(workflow_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8100, reload=True)
