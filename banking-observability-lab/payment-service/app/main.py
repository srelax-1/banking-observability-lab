import os
import logging
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from pythonjsonlogger import jsonlogger

logger = logging.getLogger("payment-service")
handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

DATABASE_URL = os.getenv("DATABASE_URL")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8003")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

app = FastAPI(title="Payment Service", version="1.0.0")


class PaymentRequest(BaseModel):
    username: str
    amount: float = Field(gt=0)
    recipient: str


@app.get("/health")
def health():
    database_status = "connected"

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("database health check failed")
        database_status = "unavailable"

    return {
        "service": "payment-service",
        "status": "healthy" if database_status == "connected" else "degraded",
        "database": database_status,
    }


async def validate_user(username: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{AUTH_SERVICE_URL}/users/{username}/validate")
            response.raise_for_status()
            return response.json().get("valid", False)
    except Exception as exc:
        logger.warning("auth service unavailable", extra={"error": str(exc), "username": username})
        raise HTTPException(status_code=503, detail="auth service unavailable")


async def send_notification(payment_id: int, payload: PaymentRequest) -> str:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.post(
                f"{NOTIFICATION_SERVICE_URL}/notify",
                json={
                    "username": payload.username,
                    "amount": payload.amount,
                    "recipient": payload.recipient,
                    "payment_id": payment_id,
                },
            )
            response.raise_for_status()
            return "sent"
    except Exception as exc:
        logger.warning(
            "notification failed but payment remains successful",
            extra={"error": str(exc), "payment_id": payment_id},
        )
        return "failed"


@app.post("/payments")
async def create_payment(payload: PaymentRequest):
    is_valid_user = await validate_user(payload.username)

    if not is_valid_user:
        raise HTTPException(status_code=403, detail="user does not exist")

    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO payments(username, amount, recipient, status, notification_status)
                    VALUES (:username, :amount, :recipient, :status, :notification_status)
                    RETURNING id
                """),
                {
                    "username": payload.username,
                    "amount": payload.amount,
                    "recipient": payload.recipient,
                    "status": "successful",
                    "notification_status": "pending",
                },
            )
            payment_id = result.scalar_one()
    except SQLAlchemyError:
        logger.exception("failed to create payment")
        raise HTTPException(status_code=503, detail="payment database unavailable")

    notification_status = await send_notification(payment_id, payload)

    try:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE payments SET notification_status=:status WHERE id=:id"),
                {"status": notification_status, "id": payment_id},
            )
    except SQLAlchemyError:
        logger.exception("failed to update notification status", extra={"payment_id": payment_id})

    logger.info(
        "payment created",
        extra={
            "payment_id": payment_id,
            "username": payload.username,
            "amount": payload.amount,
            "recipient": payload.recipient,
            "notification_status": notification_status,
        },
    )

    return {
        "payment_id": payment_id,
        "status": "successful",
        "notification_status": notification_status,
    }


@app.get("/payments/{username}")
def list_payments(username: str):
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT id, username, amount, recipient, status, notification_status, created_at
                    FROM payments
                    WHERE username=:username
                    ORDER BY id DESC
                """),
                {"username": username},
            ).mappings().all()

        return {"username": username, "payments": [dict(row) for row in rows]}
    except SQLAlchemyError:
        logger.exception("failed to list payments")
        raise HTTPException(status_code=503, detail="payment database unavailable")
