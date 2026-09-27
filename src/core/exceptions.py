from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code = 400
    code = "APP_ERROR"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class HoSoNotFound(AppError):
    status_code = 404
    code = "HO_SO_NOT_FOUND"


class ChungChiNotFound(AppError):
    status_code = 404
    code = "CHUNG_CHI_NOT_FOUND"


class TrangThaiKhongHopLe(AppError):
    status_code = 409
    code = "TRANG_THAI_KHONG_HOP_LE"


class DuLieuKhongHopLe(AppError):
    status_code = 400
    code = "DU_LIEU_KHONG_HOP_LE"


class KhongDuDieuKienCongBo(AppError):
    status_code = 400
    code = "KHONG_DU_DIEU_KIEN_CONG_BO"


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class NguonDuLieuLoi(AppError):
    status_code = 502
    code = "NGUON_DU_LIEU_LOI"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message},
        )
