import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from pythonjsonlogger import jsonlogger

logger = logging.getLogger("notification-service")
handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

app = FastAPI(title="Notification Service", version="1.0.0")


class NotificationRequest(BaseModel):
    username: str
    amount: float
    recipient: str
    payment_id: int


@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"service": "notification-service", "status": "healthy", "database": "connected"}
    except SQLAlchemyError:
        logger.exception("database health check failed")
        return {"service": "notification-service", "status": "degraded", "database": "unavailable"}


@app.post("/notify")
def notify(payload: NotificationRequest):
    message = f"{payload.username} sent you ₦{payload.amount:,.2f}"

    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO notifications(payment_id, sender, recipient, amount, message, status)
                    VALUES (:payment_id, :sender, :recipient, :amount, :message, :status)
                """),
                {
                    "payment_id": payload.payment_id,
                    "sender": payload.username,
                    "recipient": payload.recipient,
                    "amount": payload.amount,
                    "message": message,
                    "status": "unread",
                },
            )

        logger.info(
            "notification stored",
            extra={
                "sender": payload.username,
                "recipient": payload.recipient,
                "amount": payload.amount,
                "payment_id": payload.payment_id,
            },
        )

        return {
            "message": "notification stored",
            "recipient": payload.recipient,
            "payment_id": payload.payment_id,
        }

    except SQLAlchemyError:
        logger.exception("failed to store notification")
        raise HTTPException(status_code=503, detail="notification database unavailable")


@app.get("/notifications/{username}")
def list_notifications(username: str):
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT id, payment_id, sender, recipient, amount, message, status, created_at
                    FROM notifications
                    WHERE recipient=:username
                    ORDER BY id DESC
                """),
                {"username": username},
            ).mappings().all()

        return {"username": username, "notifications": [dict(row) for row in rows]}

    except SQLAlchemyError:
        logger.exception("failed to list notifications")
        raise HTTPException(status_code=503, detail="notification database unavailable")


@app.patch("/notifications/{notification_id}/read")
def mark_notification_as_read(notification_id: int):
    try:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE notifications SET status='read' WHERE id=:id"),
                {"id": notification_id},
            )

        return {"message": "notification marked as read", "notification_id": notification_id}

    except SQLAlchemyError:
        logger.exception("failed to mark notification as read")
        raise HTTPException(status_code=503, detail="notification database unavailable")