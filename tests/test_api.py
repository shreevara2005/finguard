import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import Base, get_db

# Use a separate in-memory SQLite DB for tests so we never touch finguard.db.
# StaticPool keeps a single connection alive so ":memory:" isn't wiped
# between sessions (each new SQLite connection otherwise gets a fresh DB).
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)
Base.metadata.create_all(bind=TEST_ENGINE)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def _register_and_login(username="testuser", password="testpassword123"):
    client.post("/api/v1/auth/register", json={"username": username, "password": password})
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_health_check():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_register_new_user():
    resp = client.post("/api/v1/auth/register", json={"username": "alice", "password": "supersecret1"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_register_duplicate_username_rejected():
    client.post("/api/v1/auth/register", json={"username": "bob", "password": "supersecret1"})
    resp = client.post("/api/v1/auth/register", json={"username": "bob", "password": "differentpass"})
    assert resp.status_code == 400


def test_login_success():
    client.post("/api/v1/auth/register", json={"username": "carol", "password": "carolpassword"})
    resp = client.post("/api/v1/auth/login", json={"username": "carol", "password": "carolpassword"})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_failure_wrong_password():
    client.post("/api/v1/auth/register", json={"username": "dave", "password": "davepassword"})
    resp = client.post("/api/v1/auth/login", json={"username": "dave", "password": "wrongpassword"})
    assert resp.status_code == 401


def test_login_failure_unknown_user():
    resp = client.post("/api/v1/auth/login", json={"username": "nobody", "password": "whatever123"})
    assert resp.status_code == 401


def test_optimize_requires_auth():
    resp = client.post("/api/v1/optimize-allocation", json={
        "monthly_cash": 3000,
        "debts": [{"name": "Credit Card", "balance": 5000, "apr": 0.22, "min_payment": 150}],
        "savings_goal": {"target_amount": 5000, "target_month": 24},
    })
    assert resp.status_code == 401


def test_optimize_allocation_runs_both_algorithms_returns_only_best():
    token = _register_and_login("erin", "erinpassword1")
    payload = {
        "monthly_cash": 3000,
        "debts": [
            {"name": "Credit Card", "balance": 5000, "apr": 0.22, "min_payment": 150},
            {"name": "Personal Loan", "balance": 10000, "apr": 0.07, "min_payment": 200},
        ],
        "savings_goal": {"target_amount": 5000, "target_month": 24},
        "horizon_months": 36,
    }
    resp = client.post(
        "/api/v1/optimize-allocation",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    # Only the winning algorithm's plan is surfaced -- no side-by-side comparison.
    assert body["algorithm_used"] in {"pso", "firefly"}
    assert body["feasible"] is True
    assert len(body["monthly_plan"]) > 0
    assert "Credit Card" in body["allocation_weights"]
    assert "Personal Loan" in body["allocation_weights"]
    assert "savings" in body["allocation_weights"]


def test_optimize_allocation_infeasible_input_rejected():
    token = _register_and_login("frank", "frankpassword1")
    payload = {
        "monthly_cash": 100,  # less than sum of minimum payments
        "debts": [
            {"name": "Credit Card", "balance": 5000, "apr": 0.22, "min_payment": 150},
            {"name": "Personal Loan", "balance": 10000, "apr": 0.07, "min_payment": 200},
        ],
        "savings_goal": {"target_amount": 5000, "target_month": 24},
    }
    resp = client.post(
        "/api/v1/optimize-allocation",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422  # pydantic validation error
