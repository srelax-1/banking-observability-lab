import os
import html
import httpx
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://api-gateway:8000")

app = FastAPI(title="Frontend Service", version="2.0.0")


@app.get("/health")
def health():
    return {"service": "frontend-service", "status": "healthy"}


def layout(title: str, content: str):
    return f"""
    <!doctype html>
    <html>
    <head>
        <title>{title}</title>
        <style>
            * {{
                box-sizing: border-box;
            }}

            body {{
                font-family: Arial, sans-serif;
                max-width: 1100px;
                margin: 40px auto;
                background: #f4f6f8;
                color: #111827;
            }}

            .topbar {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 24px;
            }}

            .brand {{
                font-size: 28px;
                font-weight: 800;
            }}

            .nav a {{
                margin-left: 12px;
                text-decoration: none;
                color: #111827;
                font-weight: 600;
            }}

            .hero {{
                background: #111827;
                color: white;
                padding: 40px;
                border-radius: 20px;
                margin-bottom: 24px;
            }}

            .hero h1 {{
                margin-top: 0;
                font-size: 42px;
            }}

            .hero p {{
                color: #d1d5db;
                font-size: 18px;
                line-height: 1.5;
            }}

            .grid {{
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 20px;
            }}

            .card {{
                background: white;
                padding: 24px;
                border-radius: 18px;
                box-shadow: 0 1px 8px rgba(0, 0, 0, 0.08);
                margin-bottom: 20px;
            }}

            input {{
                padding: 13px;
                margin: 8px 0;
                width: 100%;
                border: 1px solid #d1d5db;
                border-radius: 10px;
                font-size: 14px;
            }}

            button, .button {{
                padding: 12px 18px;
                cursor: pointer;
                background: #111827;
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: 700;
                text-decoration: none;
                display: inline-block;
                margin-top: 8px;
            }}

            .button.secondary {{
                background: white;
                color: #111827;
                border: 1px solid #d1d5db;
            }}

            .muted {{
                color: #6b7280;
            }}

            .success {{
                background: #ecfdf5;
                color: #065f46;
                padding: 14px;
                border-radius: 10px;
                margin-bottom: 16px;
            }}

            .error {{
                background: #fef2f2;
                color: #991b1b;
                padding: 14px;
                border-radius: 10px;
                margin-bottom: 16px;
            }}

            .item {{
                border: 1px solid #e5e7eb;
                padding: 14px;
                border-radius: 12px;
                margin-bottom: 12px;
            }}

            .badge {{
                display: inline-block;
                padding: 4px 8px;
                background: #eef2ff;
                border-radius: 999px;
                font-size: 12px;
                color: #3730a3;
                font-weight: 700;
            }}

            @media (max-width: 800px) {{
                body {{
                    margin: 20px;
                }}

                .grid {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="topbar">
            <div class="brand">Banking Observability Lab</div>
            <div class="nav">
                <a href="/">Home</a>
                <a href="/register">Create Account</a>
                <a href="/login">Login</a>
                <a href="/dashboard">Dashboard</a>
            </div>
        </div>
        {content}
    </body>
    </html>
    """


def current_user(request: Request):
    return request.cookies.get("banking_user")


async def post_json(path: str, payload: dict):
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(f"{API_GATEWAY_URL}{path}", json=payload)
    return response


async def get_json(path: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(f"{API_GATEWAY_URL}{path}")
    return response


@app.get("/", response_class=HTMLResponse)
def home():
    return layout(
        "Home",
        """
        <div class="hero">
            <h1>Simple Banking Microservice App</h1>
            <p>
                Create an account, login, make a payment, and see payment notifications.
                This app is built with multiple FastAPI services so you can practice observability,
                tracing, logging, metrics, health checks, and failure testing.
            </p>
            <a class="button" href="/register">Create Account</a>
            <a class="button secondary" href="/login">Login</a>
        </div>

        <div class="grid">
            <div class="card">
                <h2>Service Flow</h2>
                <p class="muted">
                    Frontend → API Gateway → Auth Service / Payment Service / Notification Service → Database
                </p>
            </div>
            <div class="card">
                <h2>Learning Goal</h2>
                <p class="muted">
                    Add your OpenTelemetry Collector, Prometheus, Grafana, Loki, and Tempo later.
                </p>
            </div>
        </div>
        """,
    )


@app.get("/register", response_class=HTMLResponse)
def register_page():
    return layout(
        "Create Account",
        """
        <div class="card">
            <h1>Create Account</h1>
            <p class="muted">Create a demo banking user.</p>
            <form method="post" action="/register">
                <input name="username" placeholder="Username" required>
                <input name="password" placeholder="Password" type="password" required>
                <button>Create Account</button>
            </form>
            <p class="muted">Already have an account? <a href="/login">Login here</a>.</p>
        </div>
        """,
    )


@app.post("/register", response_class=HTMLResponse)
async def register_user(username: str = Form(...), password: str = Form(...)):
    response = await post_json("/users", {"username": username, "password": password})

    if response.status_code >= 400:
        return layout(
            "Create Account Failed",
            f"""
            <div class="error">Could not create account: {html.escape(response.text)}</div>
            <a class="button" href="/register">Try Again</a>
            """,
        )

    return layout(
        "Account Created",
        f"""
        <div class="success">Account created for <strong>{html.escape(username)}</strong>.</div>
        <div class="card">
            <h2>Next step</h2>
            <p class="muted">Now login to access your dashboard.</p>
            <a class="button" href="/login">Go to Login</a>
        </div>
        """,
    )


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return layout(
        "Login",
        """
        <div class="card">
            <h1>Login</h1>
            <p class="muted">Login to access your dashboard.</p>
            <form method="post" action="/login">
                <input name="username" placeholder="Username" required>
                <input name="password" placeholder="Password" type="password" required>
                <button>Login</button>
            </form>
        </div>
        """,
    )


@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    response = await post_json("/login", {"username": username, "password": password})

    if response.status_code >= 400:
        return HTMLResponse(
            layout(
                "Login Failed",
                f"""
                <div class="error">Login failed: {html.escape(response.text)}</div>
                <a class="button" href="/login">Try Again</a>
                """,
            ),
            status_code=401,
        )

    redirect = RedirectResponse(url="/dashboard", status_code=303)
    redirect.set_cookie(key="banking_user", value=username, httponly=True)
    return redirect


@app.get("/logout")
def logout():
    redirect = RedirectResponse(url="/", status_code=303)
    redirect.delete_cookie("banking_user")
    return redirect


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    username = current_user(request)

    if not username:
        return layout(
            "Login Required",
            """
            <div class="error">You need to login before viewing the dashboard.</div>
            <a class="button" href="/login">Login</a>
            """,
        )

    payments_html = "<p class='muted'>No payments yet.</p>"
    notifications_html = "<p class='muted'>No payment notifications yet.</p>"

    try:
        payment_response = await get_json(f"/payments/{username}")
        if payment_response.status_code == 200:
            payments = payment_response.json().get("payments", [])
            if payments:
                payments_html = ""
                for payment in payments:
                    payments_html += f"""
                    <div class="item">
                        <strong>Sent ₦{float(payment["amount"]):,.2f} to {html.escape(payment["recipient"])}</strong><br>
                        <span class="muted">Payment ID: {payment["id"]}</span><br>
                        <span class="badge">{html.escape(payment["status"])}</span>
                        <span class="badge">notification: {html.escape(payment["notification_status"])}</span>
                    </div>
                    """
    except Exception as exc:
        payments_html = f"<div class='error'>Could not load payments: {html.escape(str(exc))}</div>"

    try:
        notification_response = await get_json(f"/notifications/{username}")
        if notification_response.status_code == 200:
            notifications = notification_response.json().get("notifications", [])
            if notifications:
                notifications_html = ""
                for item in notifications:
                    notifications_html += f"""
                    <div class="item">
                        <strong>{html.escape(item["message"])}</strong><br>
                        <span class="muted">From: {html.escape(item["sender"])} | Payment ID: {item["payment_id"]}</span><br>
                        <span class="badge">{html.escape(item["status"])}</span>
                    </div>
                    """
    except Exception as exc:
        notifications_html = f"<div class='error'>Could not load notifications: {html.escape(str(exc))}</div>"

    return layout(
        "Dashboard",
        f"""
        <div class="hero">
            <h1>Welcome, {html.escape(username)}</h1>
            <p>This is your banking dashboard. You can make payments and view notifications for payments sent to you.</p>
            <a class="button secondary" href="/logout">Logout</a>
        </div>

        <div class="grid">
            <div class="card">
                <h2>Make Payment</h2>
                <form method="post" action="/payments">
                    <input name="recipient" placeholder="Recipient username" required>
                    <input name="amount" placeholder="Amount" type="number" step="0.01" required>
                    <button>Send Payment</button>
                </form>
            </div>

            <div class="card">
                <h2>Notifications</h2>
                {notifications_html}
            </div>
        </div>

        <div class="card">
            <h2>Payments You Made</h2>
            {payments_html}
        </div>
        """,
    )


@app.post("/payments")
async def create_payment(request: Request, recipient: str = Form(...), amount: float = Form(...)):
    username = current_user(request)

    if not username:
        return HTMLResponse(
            layout(
                "Login Required",
                """
                <div class="error">You need to login before making payment.</div>
                <a class="button" href="/login">Login</a>
                """,
            ),
            status_code=401,
        )

    response = await post_json(
        "/payments",
        {"username": username, "recipient": recipient, "amount": amount},
    )

    if response.status_code >= 400:
        return HTMLResponse(
            layout(
                "Payment Failed",
                f"""
                <div class="error">Payment failed: {html.escape(response.text)}</div>
                <a class="button" href="/dashboard">Back to Dashboard</a>
                """,
            ),
            status_code=400,
        )

    return RedirectResponse(url="/dashboard", status_code=303)