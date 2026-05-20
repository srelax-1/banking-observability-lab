# Banking Observability Lab

A small microservice banking application designed for learning observability.

Services:

- frontend-service
- api-gateway
- auth-service
- payment-service
- notification-service
- postgres database

## Run

```bash
docker compose up --build
```

Open:

- Frontend: http://localhost:8080
- API Gateway: http://localhost:8000
- Auth Service: http://localhost:8001
- Payment Service: http://localhost:8002
- Notification Service: http://localhost:8003
- Postgres: localhost:5432

## Health checks

```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8080/health
```

## Test the flow

Create user:

```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"username":"quareeb","password":"pass123"}'
```

Login:

```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"quareeb","password":"pass123"}'
```

Create payment:

```bash
curl -X POST http://localhost:8000/payments \
  -H "Content-Type: application/json" \
  -d '{"username":"quareeb","amount":5000,"recipient":"Aisha"}'
```

List payments:

```bash
curl http://localhost:8000/payments/quareeb
```

## Failure simulation

Stop notification service:

```bash
docker compose stop notification-service
```

Create another payment. The payment still succeeds, but notification becomes `failed`.

Stop auth service:

```bash
docker compose stop auth-service
```

Create a payment again. The app returns a controlled error instead of crashing the whole system.