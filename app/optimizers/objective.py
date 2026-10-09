"""
Core simulation + objective function shared by PSO and Firefly solvers.

Decision vector layout (length = n_debts + 1):
    x[0..n_debts-1]  -> allocation weight for "extra cash" toward each debt
    x[n_debts]       -> allocation weight for "extra cash" toward savings

Weights are normalized (softmax-style clip+renormalize) to sum to 1 before
simulation, so the search space is effectively the (n_debts)-simplex and PSO/
Firefly are free to explore raw continuous values in [0, 1].

Simulation logic (debt-avalanche-compatible, but let the optimizer decide the
weights rather than hardcoding "highest APR first"):
    - Every debt always gets at least its minimum payment (if the debt's
      remaining balance is less than the minimum, only the remaining balance
      is paid).
    - "Extra cash" = monthly_cash - sum(minimum payments still owed this
      month) is distributed across still-open debts and savings according to
      the (normalized) weights.
    - When a debt is paid off, its minimum payment is no longer owed, which
      increases extra cash available for redistribution in future months
      (the weights are re-normalized over the remaining open debts + savings
      each month).
    - Interest accrues monthly on each debt's remaining balance at APR/12.
    - Savings simply accumulates (no interest modeled by default, but a
      savings_apr can optionally be supplied).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Debt:
    name: str
    balance: float
    apr: float  # annual percentage rate, e.g. 0.22 for 22%
    min_payment: float


@dataclass
class SavingsGoal:
    target_amount: float
    target_month: Optional[int] = None  # deadline in months; None = no deadline
    current_amount: float = 0.0
    apr: float = 0.0  # optional savings growth rate


@dataclass
class SimulationResult:
    total_interest_paid: float
    months_to_debt_free: int
    final_savings: float
    feasible: bool
    had_cash_shortfall: bool = False
    monthly_plan: List[dict] = field(default_factory=list)


def _normalize_weights(raw_weights: "list[float]") -> "list[float]":
    """Clip negatives to 0 and renormalize to sum to 1. Falls back to a
    uniform distribution if all weights are ~0."""
    clipped = [max(0.0, w) for w in raw_weights]
    total = sum(clipped)
    if total < 1e-9:
        n = len(clipped)
        return [1.0 / n] * n
    return [w / total for w in clipped]


def simulate(
    weights: "list[float]",
    monthly_cash: float,
    debts: List[Debt],
    savings_goal: SavingsGoal,
    horizon_months: int = 60,
    record_plan: bool = False,
) -> SimulationResult:
    """Run a month-by-month simulation for a fixed set of allocation weights
    and return totals (and optionally the full plan)."""
    n = len(debts)
    balances = [d.balance for d in debts]
    monthly_rates = [d.apr / 12.0 for d in debts]
    min_payments = [d.min_payment for d in debts]

    savings = savings_goal.current_amount
    savings_monthly_rate = savings_goal.apr / 12.0

    total_interest = 0.0
    months_to_debt_free = horizon_months
    had_cash_shortfall = False
    plan = []

    debt_weights = weights[:n]
    savings_weight = weights[n]

    for month in range(1, horizon_months + 1):
        open_mask = [b > 1e-6 for b in balances]
        if not any(open_mask):
            months_to_debt_free = min(months_to_debt_free, month - 1)
            # No debts left: 100% of monthly_cash goes to savings from here on
            savings *= (1 + savings_monthly_rate)
            savings += monthly_cash
            if record_plan:
                plan.append({
                    "month": month,
                    "debts": [{"name": d.name, "balance": 0.0, "payment": 0.0,
                               "interest": 0.0} for d in debts],
                    "savings_contribution": round(monthly_cash, 2),
                    "savings_balance": round(savings, 2),
                    "cash_shortfall": 0.0,
                })
            continue

        # Minimums owed only on open debts
        min_owed = sum(min_payments[i] for i in range(n) if open_mask[i])
        extra_cash = monthly_cash - min_owed
        shortfall = 0.0
        min_payment_scale = 1.0
        if extra_cash < 0:
            # Can't cover minimums this month: scale every minimum payment
            # down proportionally rather than fabricating uncovered cash.
            shortfall = -extra_cash
            extra_cash = 0.0
            had_cash_shortfall = True
            min_payment_scale = monthly_cash / min_owed if min_owed > 0 else 0.0

        # Renormalize weights over currently-relevant buckets (open debts + savings)
        active_weights = [debt_weights[i] if open_mask[i] else 0.0 for i in range(n)] + [savings_weight]
        active_weights = _normalize_weights(active_weights)

        month_row = {"month": month, "debts": [], "savings_contribution": 0.0,
                     "savings_balance": 0.0, "cash_shortfall": round(shortfall, 2)}

        for i, debt in enumerate(debts):
            if not open_mask[i]:
                month_row["debts"].append({"name": debt.name, "balance": 0.0,
                                            "payment": 0.0, "interest": 0.0})
                continue
            interest = balances[i] * monthly_rates[i]
            total_interest += interest
            balances[i] += interest

            payment = min_payments[i] * min_payment_scale
            payment += active_weights[i] * extra_cash
            payment = min(payment, balances[i])  # never overpay past the balance
            balances[i] -= payment

            month_row["debts"].append({
                "name": debt.name,
                "balance": round(balances[i], 2),
                "payment": round(payment, 2),
                "interest": round(interest, 2),
            })

        savings_contribution = active_weights[n] * extra_cash
        savings *= (1 + savings_monthly_rate)
        savings += savings_contribution
        month_row["savings_contribution"] = round(savings_contribution, 2)
        month_row["savings_balance"] = round(savings, 2)

        if record_plan:
            plan.append(month_row)

        if all(b <= 1e-6 for b in balances) and months_to_debt_free == horizon_months:
            months_to_debt_free = month

    feasible = all(b <= 1e-6 for b in balances) and not had_cash_shortfall

    return SimulationResult(
        total_interest_paid=total_interest,
        months_to_debt_free=months_to_debt_free,
        final_savings=savings,
        feasible=feasible,
        had_cash_shortfall=had_cash_shortfall,
        monthly_plan=plan,
    )


def objective_function(
    raw_weights: "list[float]",
    monthly_cash: float,
    debts: List[Debt],
    savings_goal: SavingsGoal,
    horizon_months: int = 60,
) -> float:
    """Fitness function to MINIMIZE. Combines:
        - total interest paid (primary cost)
        - a quadratic penalty if the savings goal isn't hit by its deadline
          (or by the end of the horizon if no deadline is given)
        - a heavy penalty for infeasible plans (can't cover minimums)
    """
    weights = _normalize_weights(list(raw_weights))
    result = simulate(weights, monthly_cash, debts, savings_goal, horizon_months)

    cost = result.total_interest_paid

    deadline = savings_goal.target_month or horizon_months
    if result.months_to_debt_free <= horizon_months:
        # crude proxy: use final savings at horizon end; a stricter version
        # would track savings-at-deadline explicitly during simulate()
        shortfall = max(0.0, savings_goal.target_amount - result.final_savings)
        cost += (shortfall ** 2) * 0.01  # penalty weight, tunable

    if not result.feasible:
        cost += 1e7  # large penalty: minimum payments not coverable

    return cost
