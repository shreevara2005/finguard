"""Firefly Algorithm (FA) solver for the allocation problem.

Fireflies are attracted to brighter (better-fitness) fireflies; brightness
decays with distance, and a small random walk keeps the swarm exploring.
"""
from __future__ import annotations

from typing import Callable, List, Tuple
import numpy as np


def run_firefly(
    fitness_fn: Callable[[List[float]], float],
    dimensions: int,
    n_fireflies: int = 40,
    n_iterations: int = 150,
    bounds: Tuple[float, float] = (0.0, 1.0),
    alpha: float = 0.2,       # randomness strength
    beta0: float = 1.0,       # attractiveness at distance 0
    gamma: float = 1.0,       # light absorption coefficient
    alpha_decay: float = 0.97,
    seed: int | None = 42,
) -> Tuple[np.ndarray, float, List[float]]:
    """Standard Firefly Algorithm (minimization). Lower fitness = brighter.
    Returns (best_position, best_fitness, fitness_history)."""
    rng = np.random.default_rng(seed)
    lo, hi = bounds
    scale = hi - lo

    positions = rng.uniform(lo, hi, size=(n_fireflies, dimensions))
    fitness = np.array([fitness_fn(p) for p in positions])

    best_idx = int(np.argmin(fitness))
    best_pos = positions[best_idx].copy()
    best_val = fitness[best_idx]
    history = [float(best_val)]

    a = alpha

    for _ in range(n_iterations):
        order = np.argsort(fitness)  # brighter (lower fitness) first
        positions = positions[order]
        fitness = fitness[order]

        new_positions = positions.copy()
        for i in range(n_fireflies):
            for j in range(n_fireflies):
                if fitness[j] < fitness[i]:  # j is brighter than i -> move i toward j
                    r = np.linalg.norm(positions[i] - positions[j])
                    beta = beta0 * np.exp(-gamma * (r ** 2))
                    randomness = a * scale * (rng.uniform(size=dimensions) - 0.5)
                    new_positions[i] = positions[i] + beta * (positions[j] - positions[i]) + randomness
        new_positions = np.clip(new_positions, lo, hi)

        new_fitness = np.array([fitness_fn(p) for p in new_positions])

        positions = new_positions
        fitness = new_fitness
        a *= alpha_decay  # cool down exploration over time

        gen_best_idx = int(np.argmin(fitness))
        if fitness[gen_best_idx] < best_val:
            best_val = fitness[gen_best_idx]
            best_pos = positions[gen_best_idx].copy()

        history.append(float(best_val))

    return best_pos, float(best_val), history
