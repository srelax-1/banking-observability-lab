import logging
import random
from fastapi import FastAPI
from pydantic import BaseModel
from pythonjsonlogger import jsonlogger

logger = logging.getLogger("notification-service")
handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

app = FastAPI(title="Notification Service", version="1.0.0")


class NotificationRequest(BaseModel):
    username: str
    amount: float
    recipient: str
    payment_id: int


@app.get("/health")
def health():
    return {"service": "notification-service", "status": "healthy"}


@app.post("/notify")
def notify(payload: NotificationRequest):
    logger.info(
        "notification sent",
        extra={
            "username": payload.username,
            "amount": payload.amount,
            "recipient": payload.recipient,
            "payment_id": payload.payment_id,
        },
    )

    return {
        "message": "notification sent",
        "channel": random.choice(["email", "sms", "push"]),
        "payment_id": payload.payment_id,
    }
