import os
import logging
import httpx
from fastapi import FastAPI, Request, HTTPException
from pythonjsonlogger import jsonlogger

logger = logging.getLogger("api-gateway")
handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8002")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8003")

app = FastAPI(title="API Gateway", version="1.0.0")


@app.middleware("http")
async def request_logger(request: Request, call_next):
    logger.info("incoming request", extra={"method": request.method, "path": request.url.path})
    response = await call_next(request)
    logger.info(
        "request completed",
        extra={"method": request.method, "path": request.url.path, "status_code": response.status_code},
    )
    return response


@app.get("/health")
async def health():
    result = {"service": "api-gateway", "status": "healthy", "dependencies": {}}

    async with httpx.AsyncClient(timeout=2.0) as client:
        for name, url in {
            "auth-service": f"{AUTH_SERVICE_URL}/health",
            "payment-service": f"{PAYMENT_SERVICE_URL}/health",
            "notification-service": f"{NOTIFICATION_SERVICE_URL}/health",
        }.items():
            try:
                response = await client.get(url)
                result["dependencies"][name] = {
                    "status": "reachable",
                    "status_code": response.status_code,
                }
            except Exception as exc:
                result["dependencies"][name] = {
                    "status": "unreachable",
                    "error": str(exc),
                }

    return result


async def forward(method: str, url: str, json_body=None):
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            response = await client.request(method, url, json=json_body)
            return response.status_code, response.json()
    except Exception as exc:
        logger.warning("downstream service unavailable", extra={"url": url, "error": str(exc)})
        raise HTTPException(status_code=503, detail="downstream service unavailable")


@app.post("/users")
async def create_user(request: Request):
    body = await request.json()
    status_code, data = await forward("POST", f"{AUTH_SERVICE_URL}/users", body)
    if status_code >= 400:
        raise HTTPException(status_code=status_code, detail=data)
    return data


@app.post("/login")
async def login(request: Request):
    body = await request.json()
    status_code, data = await forward("POST", f"{AUTH_SERVICE_URL}/login", body)
    if status_code >= 400:
        raise HTTPException(status_code=status_code, detail=data)
    return data


@app.post("/payments")
async def create_payment(request: Request):
    body = await request.json()
    status_code, data = await forward("POST", f"{PAYMENT_SERVICE_URL}/payments", body)
    if status_code >= 400:
        raise HTTPException(status_code=status_code, detail=data)
    return data


@app.get("/payments/{username}")
async def list_payments(username: str):
    status_code, data = await forward("GET", f"{PAYMENT_SERVICE_URL}/payments/{username}")
    if status_code >= 400:
        raise HTTPException(status_code=status_code, detail=data)
    return data


@app.get("/notifications/{username}")
async def list_notifications(username: str):
    status_code, data = await forward("GET", f"{NOTIFICATION_SERVICE_URL}/notifications/{username}")
    if status_code >= 400:
        raise HTTPException(status_code=status_code, detail=data)
    return data


@app.patch("/notifications/{notification_id}/read")
async def mark_notification_as_read(notification_id: int):
    status_code, data = await forward("PATCH", f"{NOTIFICATION_SERVICE_URL}/notifications/{notification_id}/read")
    if status_code >= 400:
        raise HTTPException(status_code=status_code, detail=data)
    return data