from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class DebtIn(BaseModel):
    name: str
    balance: float = Field(..., gt=0)
    apr: float = Field(..., ge=0, le=1, description="Decimal APR, e.g. 0.22 for 22%")
    min_payment: float = Field(..., ge=0)


class SavingsGoalIn(BaseModel):
    target_amount: float = Field(..., ge=0)
    target_month: Optional[int] = Field(None, ge=1, le=360)
    current_amount: float = Field(0.0, ge=0)
    apr: float = Field(0.0, ge=0, le=1)


class OptimizeRequest(BaseModel):
    monthly_cash: float = Field(..., gt=0)
    debts: List[DebtIn]
    savings_goal: SavingsGoalIn
    horizon_months: int = Field(60, ge=1, le=360)
    # Note: both PSO and the Firefly Algorithm always run; the endpoint
    # compares them and returns whichever converged to a lower-cost plan.

    @model_validator(mode="after")
    def check_min_payments_possible(self):
        total_min = sum(d.min_payment for d in self.debts)
        if total_min > self.monthly_cash:
            raise ValueError(
                f"monthly_cash ({self.monthly_cash}) is less than the sum of "
                f"minimum payments ({total_min}); the plan is infeasible as entered."
            )
        return self


class DebtMonthRow(BaseModel):
    name: str
    balance: float
    payment: float
    interest: float


class MonthRow(BaseModel):
    month: int
    debts: List[DebtMonthRow]
    savings_contribution: float
    savings_balance: float
    cash_shortfall: float


class OptimizeResponse(BaseModel):
    algorithm_used: str  # "pso" or "firefly" -- whichever converged to the better plan
    total_interest_paid: float
    months_to_debt_free: int
    final_savings: float
    feasible: bool
    allocation_weights: dict
    monthly_plan: List[MonthRow]


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=72)
