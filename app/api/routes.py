from __future__ import annotations

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import (
    authenticate_user,
    create_access_token,
    create_user,
    get_current_user,
    get_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.db import get_db
from app.db_models import User
from app.models import (
    LoginRequest,
    RegisterRequest,
    OptimizeRequest,
    OptimizeResponse,
    Token,
)
from app.optimizers.objective import Debt, SavingsGoal, objective_function, simulate, _normalize_weights
from app.optimizers.pso import run_pso
from app.optimizers.firefly import run_firefly

router = APIRouter()


@router.post("/auth/register", response_model=Token, tags=["auth"])
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if get_user(db, payload.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    user = create_user(db, payload.username, payload.password)
    token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=token)


@router.post("/auth/login", response_model=Token, tags=["auth"])
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=token)


def _run_algorithm(name: str, fitness_fn, dims: int):
    if name == "pso":
        pos, val, _ = run_pso(fitness_fn, dims)
    elif name == "firefly":
        pos, val, _ = run_firefly(fitness_fn, dims)
    else:
        raise ValueError(f"Unknown algorithm: {name}")
    return _normalize_weights(list(pos)), val


@router.post("/optimize-allocation", response_model=OptimizeResponse, tags=["optimization"])
def optimize_allocation(req: OptimizeRequest, current_user: User = Depends(get_current_user)):
    debts = [Debt(name=d.name, balance=d.balance, apr=d.apr, min_payment=d.min_payment) for d in req.debts]
    goal = SavingsGoal(
        target_amount=req.savings_goal.target_amount,
        target_month=req.savings_goal.target_month,
        current_amount=req.savings_goal.current_amount,
        apr=req.savings_goal.apr,
    )
    dims = len(debts) + 1

    def fitness(x):
        return objective_function(x, req.monthly_cash, debts, goal, req.horizon_months)

    # Always run both solvers internally and keep only whichever converged to
    # a lower-cost plan (less total interest + smaller savings-goal
    # shortfall) -- the API only ever surfaces that one winning plan.
    best_weights, best_val, best_name = None, float("inf"), None
    for name in ["pso", "firefly"]:
        weights, val = _run_algorithm(name, fitness, dims)
        if val < best_val:
            best_val, best_weights, best_name = val, weights, name

    best_sim = simulate(best_weights, req.monthly_cash, debts, goal, req.horizon_months, record_plan=True)

    weight_map = {debts[i].name: round(best_weights[i], 4) for i in range(len(debts))}
    weight_map["savings"] = round(best_weights[-1], 4)

    return OptimizeResponse(
        algorithm_used=best_name,
        total_interest_paid=round(best_sim.total_interest_paid, 2),
        months_to_debt_free=best_sim.months_to_debt_free,
        final_savings=round(best_sim.final_savings, 2),
        feasible=best_sim.feasible,
        allocation_weights=weight_map,
        monthly_plan=best_sim.monthly_plan,
    )
