"""
Minigame logic ported from the AutoHotkey fishing macro.

This module implements a configuration-driven controller that decides corrective
actions for a minigame "indicator" (the moving cursor/needle inside a fish bar).
It doesn't interact with GUI or input devices; it provides the decision logic
(your AHK or other automation layer can call into this to get what to do next).

Contract (inputs/outputs):
- Inputs: minigame state described by a dict or named args:
    - indicator: float (0..1) current normalized position of the indicator along the bar
    - arrow: "left"|"right"|None (direction the game is pushing the indicator)
    - stable: bool (whether the current state is "stable" or "unstable")
    - delta_time: float seconds since last update (optional)
- Outputs: action dict:
    - action: "none"|"move_left"|"move_right"
    - intensity: float (0..1) suggested strength / duration fraction
    - note: optional human readable note

Assumptions / simplifications vs original AHK script:
- Positions are normalized to 0..1 (0 = left, 1 = right).
- Fish bar is a centered subrange of the full bar; side bars and white bar logic
  are approximated using ratios and tolerances from the original settings.
- Multipliers/divisions are used to compute intensity as in the original script.

Edge cases handled:
- indicator outside 0..1 is clamped
- missing arrow/stable state treated as conservative (smaller corrections)

Usage:
    from minigame_logic import MinigameController
    cfg = {...}
    ctl = MinigameController(cfg)
    action = ctl.decide(indicator=0.82, arrow='right', stable=False)

"""
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict


@dataclass
class MinigameConfig:
    # Tolerances (normalized units)
    fish_bar_half_width: float = 0.08  # half-width of the fish bar (so full width = 2*half)
    white_bar_half_width: float = 0.02

    # Scanning delay (used by callers, returned for reference)
    scan_delay: float = 0.02

    # Side bar ratio (how far from center the side zones are) - not used directly
    side_bar_ratio: float = 0.5
    side_delay: float = 0.02

    # Stabililty multipliers/divisions used to compute intensity
    stable_right_multiplier: float = 1.0
    stable_right_division: float = 1.0
    stable_left_multiplier: float = 1.0
    stable_left_division: float = 1.0

    unstable_right_multiplier: float = 1.5
    unstable_right_division: float = 1.0
    unstable_left_multiplier: float = 1.5
    unstable_left_division: float = 1.0

    # Ankle-break multipliers (intended for very quick counter-actions)
    right_ankle_break_multiplier: float = 2.0
    left_ankle_break_multiplier: float = 2.0

    # Minimal action intensity and max clamp
    min_intensity: float = 0.05
    max_intensity: float = 1.0


class MinigameController:
    def __init__(self, cfg: Optional[MinigameConfig] = None):
        self.cfg = cfg or MinigameConfig()

    def _clamp01(self, v: float) -> float:
        if v is None:
            return 0.0
        return max(0.0, min(1.0, v))

    def _compute_target(self) -> float:
        # The fish bar is centered in the full bar; target is center (0.5)
        return 0.5

    def _inside_fish_bar(self, indicator: float) -> bool:
        target = self._compute_target()
        half = self.cfg.fish_bar_half_width
        return (target - half) <= indicator <= (target + half)

    def decide(self, indicator: float, arrow: Optional[str] = None, stable: bool = True,
               delta_time: Optional[float] = None) -> Dict:
        """
        Decide corrective action for one step of the minigame.

        indicator: normalized 0..1 position
        arrow: 'left'|'right' or None
        stable: whether minigame is currently in a stable state
        delta_time: time since last decision (unused for now)

        Returns a dict: {action, intensity, note}
        """
        indicator = self._clamp01(indicator)
        target = self._compute_target()
        error = indicator - target  # positive -> right of center

        # If already comfortably inside fish bar, do nothing
        if self._inside_fish_bar(indicator):
            return {"action": "none", "intensity": 0.0, "note": "inside fish bar"}

        # Decide correction direction: move toward center
        direction = "move_left" if error > 0 else "move_right"

        # Determine multiplier/division depending on side and stable/unstable
        if error > 0:  # indicator is on the right side -> move left
            if stable:
                mult = self.cfg.stable_left_multiplier
                div = self.cfg.stable_left_division
            else:
                mult = self.cfg.unstable_left_multiplier
                div = self.cfg.unstable_left_division
        else:  # indicator is on the left side -> move right
            if stable:
                mult = self.cfg.stable_right_multiplier
                div = self.cfg.stable_right_division
            else:
                mult = self.cfg.unstable_right_multiplier
                div = self.cfg.unstable_right_division

        # Base intensity proportional to distance from center normalized by max possible distance (0.5)
        base_intensity = abs(error) / 0.5  # maps 0..0.5 -> 0..1

        # Apply multiplier/division and clamp
        intensity = base_intensity * (mult / max(div, 1e-6))

        # If arrow indicates pushing in a particular direction, increase intensity
        if arrow == "right" and direction == "move_left":
            intensity *= 1.2
        elif arrow == "left" and direction == "move_right":
            intensity *= 1.2

        # Apply ankle-break for extreme cases (indicator very close to edge)
        edge_threshold = 0.9
        if indicator > edge_threshold:
            intensity *= self.cfg.right_ankle_break_multiplier
        elif indicator < (1.0 - edge_threshold):
            intensity *= self.cfg.left_ankle_break_multiplier

        # Final clamps
        intensity = max(self.cfg.min_intensity, intensity)
        intensity = min(self.cfg.max_intensity, intensity)

        note = f"error={error:.3f} stable={stable} arrow={arrow}"
        return {"action": direction, "intensity": float(intensity), "note": note}


# A simple step simulator to allow light unit testing or tuning
def simulate(controller: MinigameController, initial_indicator: float,
             steps: int = 50, step_dt: float = 0.05, noise: float = 0.0) -> Tuple[float, list]:
    """
    Simulate the indicator for a number of steps, applying controller.decide at each step.
    This sim is simplistic: it applies the controller's intensity as a velocity toward center.

    Returns the final indicator and a history of (indicator, action, intensity) tuples.
    """
    import random

    indicator = controller._clamp01(initial_indicator)
    history = []
    for i in range(steps):
        # For simulation, pretend arrow is random push
        arrow = random.choice([None, "left", "right"]) if noise > 0 else None
        stable = True if random.random() > 0.1 else False if noise > 0 else True
        decision = controller.decide(indicator=indicator, arrow=arrow, stable=stable, delta_time=step_dt)

        # Convert intensity to a velocity toward center
        if decision["action"] == "none":
            velocity = 0.0
        elif decision["action"] == "move_left":
            velocity = -decision["intensity"] * 0.02  # tuning constant for sim
        else:
            velocity = decision["intensity"] * 0.02

        # Arrow/environmental push (small)
        env_push = 0.0
        if arrow == "left":
            env_push -= 0.01
        elif arrow == "right":
            env_push += 0.01

        # Update indicator with velocity + environment + noise
        indicator = controller._clamp01(indicator + velocity + env_push + (random.random() - 0.5) * noise)
        history.append((indicator, decision["action"], decision["intensity"]))

    return indicator, history


# Quick example / self-test
if __name__ == "__main__":
    cfg = MinigameConfig()
    ctl = MinigameController(cfg)

    print("Example decisions:")
    for pos in [0.02, 0.1, 0.3, 0.45, 0.6, 0.85, 0.98]:
        d = ctl.decide(indicator=pos, arrow=None, stable=True)
        print(f"pos={pos:.2f} -> {d}")

    # Run a small simulation
    final, hist = simulate(ctl, initial_indicator=0.9, steps=40, noise=0.02)
    print(f"Sim final indicator: {final:.3f}")
    print("Last 5 steps:")
    for x in hist[-5:]:
        print(x)
