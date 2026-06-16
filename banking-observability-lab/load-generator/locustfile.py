import os
import random
import string
from itertools import count

from locust import HttpUser, between, task


PASSWORD = os.getenv("LOADGEN_PASSWORD", "LoadTest123!")
USER_PREFIX = os.getenv("LOADGEN_USER_PREFIX", "loadtest")
MIN_PAYMENT = float(os.getenv("LOADGEN_MIN_PAYMENT", "1000"))
MAX_PAYMENT = float(os.getenv("LOADGEN_MAX_PAYMENT", "5000000"))

# Each Locust worker process gets a counter. A random suffix prevents clashes
# across repeated runs and distributed workers.
RUN_SUFFIX = os.getenv(
    "LOADGEN_RUN_ID",
    "".join(random.choices(string.ascii_lowercase + string.digits, k=6)),
)
USER_COUNTER = count(1)


class BankingUser(HttpUser):
    """Simulates a banking customer through the API Gateway.

    Every virtual user creates two accounts:
    - its own sender account
    - a recipient account

    It then generates payments and reads both payment and notification data.
    """

    wait_time = between(1, 4)

    def on_start(self):
        number = next(USER_COUNTER)
        self.username = f"{USER_PREFIX}-{RUN_SUFFIX}-{number}"
        self.recipient = f"{self.username}-recipient"

        self._ensure_user(self.username)
        self._ensure_user(self.recipient)
        self._login()

    def _ensure_user(self, username: str) -> None:
        with self.client.post(
            "/users",
            json={"username": username, "password": PASSWORD},
            name="POST /users",
            catch_response=True,
        ) as response:
            # 200/201 means created. 409 is also acceptable when reusing a run ID.
            if response.status_code in (200, 201, 409):
                response.success()
            else:
                response.failure(
                    f"Could not create {username}: {response.status_code} {response.text}"
                )

    def _login(self) -> None:
        with self.client.post(
            "/login",
            json={"username": self.username, "password": PASSWORD},
            name="POST /login",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                self.token = response.json().get("token")
                response.success()
            else:
                response.failure(
                    f"Login failed: {response.status_code} {response.text}"
                )

    @task(6)
    def make_payment(self):
        amount = round(random.uniform(MIN_PAYMENT, MAX_PAYMENT), 2)
        with self.client.post(
            "/payments",
            json={
                "username": self.username,
                "recipient": self.recipient,
                "amount": amount,
            },
            name="POST /payments",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "successful":
                    response.success()
                else:
                    response.failure(f"Unexpected payment response: {data}")
            else:
                response.failure(
                    f"Payment failed: {response.status_code} {response.text}"
                )

    @task(3)
    def list_my_payments(self):
        self.client.get(
            f"/payments/{self.username}",
            name="GET /payments/:username",
        )

    @task(3)
    def list_recipient_notifications(self):
        self.client.get(
            f"/notifications/{self.recipient}",
            name="GET /notifications/:username",
        )

    @task(1)
    def check_gateway_health(self):
        self.client.get("/health", name="GET /health")
