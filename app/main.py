from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.db import Base, engine, SessionLocal
from app.db_models import User
from app.auth import hash_password


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Creates the users table if it doesn't exist yet (SQLite/Postgres both fine).
    # For a bigger production schema, swap this for Alembic migrations.
    Base.metadata.create_all(bind=engine)

    # Seed a demo account so the API is testable immediately after `docker
    # compose up`, without requiring a manual /auth/register call first.
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "demo").first():
            db.add(User(username="demo", hashed_password=hash_password("demopassword")))
            db.commit()
    finally:
        db.close()

    yield  # app runs here


app = FastAPI(
    title="FinGuard API",
    description="Algorithmic Debt & Savings Optimizer -- PSO / Firefly powered.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to your frontend's origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/health", tags=["meta"])
def health_check():
    return {"status": "ok"}
