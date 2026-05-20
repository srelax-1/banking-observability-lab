import os
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from pythonjsonlogger import jsonlogger

logger = logging.getLogger("auth-service")
handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

app = FastAPI(title="Auth Service", version="1.0.0")


class UserRequest(BaseModel):
    username: str
    password: str


@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"service": "auth-service", "status": "healthy", "database": "connected"}
    except SQLAlchemyError:
        logger.exception("database health check failed")
        return {"service": "auth-service", "status": "degraded", "database": "unavailable"}


@app.post("/users")
def create_user(payload: UserRequest):
    try:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO users(username, password) VALUES (:username, :password)"),
                {"username": payload.username, "password": payload.password},
            )
        logger.info("user created", extra={"username": payload.username})
        return {"message": "user created", "username": payload.username}
    except SQLAlchemyError:
        logger.exception("failed to create user")
        raise HTTPException(status_code=409, detail="user already exists or database error")


@app.post("/login")
def login(payload: UserRequest):
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT username FROM users WHERE username=:username AND password=:password"),
                {"username": payload.username, "password": payload.password},
            ).fetchone()

        if not row:
            raise HTTPException(status_code=401, detail="invalid username or password")

        logger.info("user login successful", extra={"username": payload.username})
        return {
            "message": "login successful",
            "username": payload.username,
            "token": f"demo-token-for-{payload.username}",
            "issued_at": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except SQLAlchemyError:
        logger.exception("login failed due to database error")
        raise HTTPException(status_code=503, detail="auth database unavailable")


@app.get("/users/{username}/validate")
def validate_user(username: str):
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT username FROM users WHERE username=:username"),
                {"username": username},
            ).fetchone()

        return {"username": username, "valid": bool(row)}
    except SQLAlchemyError:
        logger.exception("user validation failed")
        raise HTTPException(status_code=503, detail="auth service database unavailable")
