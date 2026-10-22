"""Start the real score application. Never seeds, patches providers or migrates databases."""
import os
from pathlib import Path
os.chdir(Path(__file__).resolve().parent)

from sqlalchemy import text
from src.core.config import get_settings
from src.core.database import get_engine

settings = get_settings()
# No simulated external examination sources in a real run.
if settings.thpt_provider == "mock":
    settings.thpt_provider = "http" if settings.thpt_api_url else "disabled"
if settings.dgnl_provider == "mock":
    settings.dgnl_provider = "http" if settings.dgnl_api_url else "disabled"
print(f"THPT provider: {settings.thpt_provider}; DGNL provider: {settings.dgnl_provider}", flush=True)
try:
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
        columns = set(connection.execute(text("SELECT table_name,column_name FROM information_schema.columns WHERE table_schema='public'")))
        required = {('thi_sinh','password'), ('thi_sinh','email'), ('nguyen_vong_sinh_vien','cong_bo_at'),
            ('nguyen_vong_sinh_vien','chot_ket_qua_at'), ('nguyen_vong_sinh_vien','nguon_ket_qua'), ('nguyen_vong_sinh_vien','diem_trace')}
        missing = sorted(required - columns)
        print("Database connected. Missing application columns: " + (", ".join(f"{t}.{c}" for t,c in missing) or "none"), flush=True)
        enum = connection.execute(text("SELECT udt_name FROM information_schema.columns WHERE table_schema='public' AND table_name='nguyen_vong_sinh_vien' AND column_name='trang_thai'" )).scalar()
        print(f"Profile status enum: {enum}; application expects trang_thai_ho_so", flush=True)
except Exception as error:
    # Connection exceptions may include passwords/URLs; expose only the exception class.
    print(f"Database preflight failed: {type(error).__name__}. No database changes were made.", flush=True)

import uvicorn
from app import app
uvicorn.run(app, host="127.0.0.1", port=8100)
