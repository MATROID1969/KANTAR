import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

# SQLite fejlesztéshez; PostgreSQL-re váltáshoz set DATABASE_URL env változót
# pl. DATABASE_URL=postgresql://user:pass@localhost/kantar
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/kantar.db")

APP_TITLE = "Kantar Projekt Nyilvántartó"

# Developer user – amíg nincs multi-user auth, mindenki ezzel a userrel lép be
DEV_USER_ID = 1
