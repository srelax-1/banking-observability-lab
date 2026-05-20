import os
import httpx
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://api-gateway:8000")

app = FastAPI(title="Frontend Service", version="1.0.0")


@app.get("/health")
def health():
    return {"service": "frontend-service", "status": "healthy"}


def page(content: str):
    return f"""
    <!doctype html>
    <html>
    <head>
        <title>Banking Observability Lab</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; background: #f7f7f7; }}
            .card {{ background: white; padding: 20px; margin-bottom: 20px; border-radius: 12px; box-shadow: 0 1px 5px #ddd; }}
            input {{ padding: 10px; margin: 5px; width: 220px; }}
            button {{ padding: 10px 15px; cursor: pointer; }}
            pre {{ background: #111; color: #0f0; padding: 15px; border-radius: 8px; overflow-x: auto; }}
        </style>
    </head>
    <body>
        <h1>Banking Observability Lab</h1>
        {content}
    </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
def home():
    return page("""
    <div class="card">
        <h2>Create User</h2>
        <form method="post" action="/users">
            <input name="username" placeholder="Username" required>
            <input name="password" placeholder="Password" required>
            <button>Create</button>
        </form>
    </div>

    <div class="card">
        <h2>Login</h2>
        <form method="post" action="/login">
            <input name="username" placeholder="Username" required>
            <input name="password" placeholder="Password" required>
            <button>Login</button>
        </form>
    </div>

    <div class="card">
        <h2>Create Payment</h2>
        <form method="post" action="/payments">
            <input name="username" placeholder="Username" required>
            <input name="amount" placeholder="Amount" required>
            <input name="recipient" placeholder="Recipient" required>
            <button>Pay</button>
        </form>
    </div>

    <div class="card">
        <h2>List Payments</h2>
        <form method="get" action="/payments">
            <input name="username" placeholder="Username" required>
            <button>Search</button>
        </form>
    </div>
    """)


@app.post("/users", response_class=HTMLResponse)
async def create_user(username: str = Form(...), password: str = Form(...)):
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(f"{API_GATEWAY_URL}/users", json={"username": username, "password": password})
    return page(f"<div class='card'><h2>Result</h2><pre>{response.text}</pre><a href='/'>Back</a></div>")


@app.post("/login", response_class=HTMLResponse)
async def login(username: str = Form(...), password: str = Form(...)):
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(f"{API_GATEWAY_URL}/login", json={"username": username, "password": password})
    return page(f"<div class='card'><h2>Result</h2><pre>{response.text}</pre><a href='/'>Back</a></div>")


@app.post("/payments", response_class=HTMLResponse)
async def create_payment(username: str = Form(...), amount: float = Form(...), recipient: str = Form(...)):
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(
            f"{API_GATEWAY_URL}/payments",
            json={"username": username, "amount": amount, "recipient": recipient},
        )
    return page(f"<div class='card'><h2>Result</h2><pre>{response.text}</pre><a href='/'>Back</a></div>")


@app.get("/payments", response_class=HTMLResponse)
async def list_payments(username: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(f"{API_GATEWAY_URL}/payments/{username}")
    return page(f"<div class='card'><h2>Payments</h2><pre>{response.text}</pre><a href='/'>Back</a></div>")
