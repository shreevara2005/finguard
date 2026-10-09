import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.optimizers.objective import Debt, SavingsGoal, objective_function, simulate, _normalize_weights
from app.optimizers.pso import run_pso
from app.optimizers.firefly import run_firefly


DEBTS = [
    Debt(name="Credit Card", balance=5000, apr=0.22, min_payment=150),
    Debt(name="Personal Loan", balance=10000, apr=0.07, min_payment=200),
]
GOAL = SavingsGoal(target_amount=5000, target_month=24)
MONTHLY_CASH = 3000
HORIZON = 60


def _fitness(x):
    return objective_function(x, MONTHLY_CASH, DEBTS, GOAL, HORIZON)


def test_normalize_weights_sums_to_one():
    w = _normalize_weights([0.2, -1.0, 3.5])
    assert abs(sum(w) - 1.0) < 1e-9
    assert all(v >= 0 for v in w)


def test_normalize_weights_handles_all_zero():
    w = _normalize_weights([0.0, 0.0, 0.0])
    assert abs(sum(w) - 1.0) < 1e-9


def test_simulate_pays_off_debts_with_sufficient_cash():
    weights = [0.5, 0.5, 0.0]
    result = simulate(weights, MONTHLY_CASH, DEBTS, GOAL, HORIZON)
    assert result.feasible is True
    assert result.total_interest_paid > 0
    assert result.months_to_debt_free <= HORIZON


def test_simulate_infeasible_when_cash_below_minimums():
    weights = [0.5, 0.5, 0.0]
    result = simulate(weights, 100, DEBTS, GOAL, HORIZON)  # 100 < 150+200 minimums
    assert result.feasible is False


def test_pso_converges_and_beats_naive_baseline():
    dims = len(DEBTS) + 1
    pos, val, history = run_pso(_fitness, dims, n_particles=20, n_iterations=40)
    assert history[-1] <= history[0]  # fitness should not get worse over time

    naive_weights = [1 / dims] * dims
    naive_val = _fitness(naive_weights)
    assert val <= naive_val  # optimizer should be at least as good as naive equal split


def test_firefly_converges_and_beats_naive_baseline():
    dims = len(DEBTS) + 1
    pos, val, history = run_firefly(_fitness, dims, n_fireflies=20, n_iterations=40)
    assert history[-1] <= history[0]

    naive_weights = [1 / dims] * dims
    naive_val = _fitness(naive_weights)
    assert val <= naive_val


def test_pso_favors_higher_apr_debt():
    """Sanity check: optimizer should send more of the extra cash toward the
    higher-APR credit card than the lower-APR loan (avalanche-like behavior
    should emerge from the objective, not be hardcoded)."""
    dims = len(DEBTS) + 1
    pos, val, _ = run_pso(_fitness, dims, n_particles=30, n_iterations=80)
    weights = _normalize_weights(list(pos))
    assert weights[0] > weights[1]  # Credit Card (22% APR) > Personal Loan (7% APR)
