"""Quick manual sanity check: do PSO and Firefly converge to sensible,
comparable allocation strategies on hardcoded dummy data?

    $5,000 credit card @ 22% APR, min payment $150
    $10,000 loan       @  7% APR, min payment $200
    $3,000 monthly cash available
    Savings goal: $5,000 within 24 months
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.optimizers.objective import Debt, SavingsGoal, objective_function, simulate, _normalize_weights
from app.optimizers.pso import run_pso
from app.optimizers.firefly import run_firefly

debts = [
    Debt(name="Credit Card", balance=5000, apr=0.22, min_payment=150),
    Debt(name="Personal Loan", balance=10000, apr=0.07, min_payment=200),
]
goal = SavingsGoal(target_amount=5000, target_month=24)
monthly_cash = 3000
horizon = 60

def fitness(x):
    return objective_function(x, monthly_cash, debts, goal, horizon)

dims = len(debts) + 1

print("=== Running PSO ===")
pso_pos, pso_val, pso_hist = run_pso(fitness, dims, n_particles=40, n_iterations=120)
pso_w = _normalize_weights(list(pso_pos))
print("PSO best weights (CC, Loan, Savings):", [round(w, 3) for w in pso_w])
print("PSO best fitness:", round(pso_val, 2))
print("PSO fitness improved:", pso_hist[0], "->", pso_hist[-1])

print("\n=== Running Firefly ===")
fa_pos, fa_val, fa_hist = run_firefly(fitness, dims, n_fireflies=40, n_iterations=120)
fa_w = _normalize_weights(list(fa_pos))
print("Firefly best weights (CC, Loan, Savings):", [round(w, 3) for w in fa_w])
print("Firefly best fitness:", round(fa_val, 2))
print("Firefly fitness improved:", fa_hist[0], "->", fa_hist[-1])

print("\n=== Simulated outcome using PSO weights ===")
result = simulate(pso_w, monthly_cash, debts, goal, horizon, record_plan=False)
print("Total interest paid:", round(result.total_interest_paid, 2))
print("Months to debt-free:", result.months_to_debt_free)
print("Final savings:", round(result.final_savings, 2))
print("Feasible:", result.feasible)

# Sanity comparison: a naive "equal split" strategy should generally do worse
naive_w = [1/3, 1/3, 1/3]
naive_result = simulate(naive_w, monthly_cash, debts, goal, horizon)
print("\n=== Naive equal-split baseline ===")
print("Total interest paid:", round(naive_result.total_interest_paid, 2))
print("Months to debt-free:", naive_result.months_to_debt_free)
print("Final savings:", round(naive_result.final_savings, 2))
