"""Particle Swarm Optimization (PSO) solver for the allocation problem."""
from __future__ import annotations

from typing import Callable, List, Tuple
import numpy as np


def run_pso(
    fitness_fn: Callable[[List[float]], float],
    dimensions: int,
    n_particles: int = 40,
    n_iterations: int = 150,
    bounds: Tuple[float, float] = (0.0, 1.0),
    w: float = 0.7,          # inertia weight
    c1: float = 1.5,         # cognitive coefficient
    c2: float = 1.5,         # social coefficient
    seed: int | None = 42,
) -> Tuple[np.ndarray, float, List[float]]:
    """Standard PSO. Returns (best_position, best_fitness, fitness_history)."""
    rng = np.random.default_rng(seed)
    lo, hi = bounds

    positions = rng.uniform(lo, hi, size=(n_particles, dimensions))
    velocities = rng.uniform(-abs(hi - lo), abs(hi - lo), size=(n_particles, dimensions)) * 0.1

    personal_best_pos = positions.copy()
    personal_best_val = np.array([fitness_fn(p) for p in positions])

    global_best_idx = int(np.argmin(personal_best_val))
    global_best_pos = personal_best_pos[global_best_idx].copy()
    global_best_val = personal_best_val[global_best_idx]

    history = [float(global_best_val)]

    for _ in range(n_iterations):
        r1 = rng.uniform(0, 1, size=(n_particles, dimensions))
        r2 = rng.uniform(0, 1, size=(n_particles, dimensions))

        velocities = (
            w * velocities
            + c1 * r1 * (personal_best_pos - positions)
            + c2 * r2 * (global_best_pos - positions)
        )
        positions = np.clip(positions + velocities, lo, hi)

        values = np.array([fitness_fn(p) for p in positions])

        improved = values < personal_best_val
        personal_best_pos[improved] = positions[improved]
        personal_best_val[improved] = values[improved]

        gen_best_idx = int(np.argmin(personal_best_val))
        if personal_best_val[gen_best_idx] < global_best_val:
            global_best_val = personal_best_val[gen_best_idx]
            global_best_pos = personal_best_pos[gen_best_idx].copy()

        history.append(float(global_best_val))

    return global_best_pos, float(global_best_val), history
