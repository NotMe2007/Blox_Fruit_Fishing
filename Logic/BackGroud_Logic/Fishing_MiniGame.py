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
    # Control stat from fishing rod (affects max duration calculations)
    control: float = 0.0  # 0.15-0.25+ based on rod stats
    
    # Color detection tolerances (from AHK script)
    fish_bar_color_tolerance: int = 5  # Brown fish color detection
    white_bar_color_tolerance: int = 15  # White bar detection
    arrow_color_tolerance: int = 6  # Arrow/indicator detection
    
    # Tolerances (normalized units)
    fish_bar_half_width: float = 0.08  # half-width of the fish bar (so full width = 2*half)
    white_bar_half_width: float = 0.02

    # Scanning delay (used by callers, returned for reference) - from AHK: 10ms
    scan_delay: float = 0.01  # 10ms converted to seconds
    
    # Dynamic fish center position (can be updated during minigame)
    fish_center: float = 0.5  # Default to center, updated by detection

    # Side bar ratio and delay (from AHK script)
    side_bar_ratio: float = 0.7  # AHK default
    side_delay: float = 0.4  # 400ms converted to seconds

    # Stability multipliers/divisions (from AHK script - exact values)
    stable_right_multiplier: float = 2.36
    stable_right_division: float = 1.55
    stable_left_multiplier: float = 1.211
    stable_left_division: float = 1.12

    # Unstable multipliers/divisions (from AHK script - exact values)
    unstable_right_multiplier: float = 2.665
    unstable_right_division: float = 1.5
    unstable_left_multiplier: float = 2.19
    unstable_left_division: float = 1.0

    # Ankle-break multipliers (from AHK script - exact values)
    right_ankle_break_multiplier: float = 0.75
    left_ankle_break_multiplier: float = 0.45

    # Pixel scaling and deadzone calculations (calculated dynamically)
    pixel_scaling: float = 1.0  # will be calculated based on bar width
    deadzone: float = 0.02  # small deadzone for stability (normalized)
    deadzone2: float = 0.04  # larger deadzone for aggressive actions (normalized)
    
    # Boundary calculations (normalized, calculated dynamically)
    max_left_bar: float = 0.15  # left boundary
    max_right_bar: float = 0.85  # right boundary

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
        # The fish bar position - can be dynamic based on fish detection
        return self.cfg.fish_center

    def _inside_fish_bar(self, indicator: float) -> bool:
        target = self._compute_target()
        half = self.cfg.fish_bar_half_width
        return (target - half) <= indicator <= (target + half)

    def decide(self, indicator: float, arrow: Optional[str] = None, stable: bool = True,
               delta_time: Optional[float] = None) -> Dict:
        """
        Decide corrective action based on AHK minigame logic with 6 action types.
        
        Action types (matching AHK script):
        0 = stabilize (short click for minor correction)
        1 = stable left tracking (moderate left movement with counter-strafe)
        2 = stable right tracking (moderate right movement with counter-strafe)
        3 = max left boundary (indicator is too far right, strong left correction)
        4 = max right boundary (indicator is too far left, strong right correction)
        5 = unstable left (aggressive left movement for unstable conditions)
        6 = unstable right (aggressive right movement for unstable conditions)

        indicator: normalized 0..1 position (white bar position)
        arrow: 'left'|'right' or None (game pushing direction)
        stable: whether minigame is currently in a stable state
        delta_time: time since last decision (for adaptive duration)

        Returns a dict: {action, intensity, note, action_type, duration_factor}
        """
        indicator = self._clamp01(indicator)
        fish_center = self._compute_target()
        
        # Calculate direction from white bar to fish center
        direction = indicator - fish_center  # positive = white bar is right of fish
        distance_factor = abs(direction) / self.cfg.white_bar_half_width
        
        # Check boundary conditions (AHK Action 3 & 4) - based on indicator position
        if indicator < self.cfg.max_left_bar:
            # Indicator is at extreme left - force right movement  
            return {
                "action": "move_right", 
                "intensity": 1.0, 
                "note": "max_right_boundary",
                "action_type": 4,
                "duration_factor": self.cfg.side_delay
            }
        elif indicator > self.cfg.max_right_bar:
            # Indicator is at extreme right - force left movement
            return {
                "action": "move_left", 
                "intensity": 1.0, 
                "note": "max_left_boundary", 
                "action_type": 3,
                "duration_factor": self.cfg.side_delay
            }
        
        # Normal tracking logic based on deadzone thresholds
        if abs(direction) <= self.cfg.deadzone:
            # AHK Action 0: Stabilize - small correction
            return {
                "action": "stabilize",
                "intensity": 0.1,
                "note": "stabilizing",
                "action_type": 0,
                "duration_factor": 0.01  # Very short click
            }
            
        elif self.cfg.deadzone < abs(direction) <= self.cfg.deadzone2:
            # AHK Action 1 & 2: Stable tracking
            if direction > 0:  # Move left (Action 1)
                intensity = abs(direction) * self.cfg.stable_left_multiplier * self.cfg.pixel_scaling
                adaptive_duration = 0.5 + 0.5 * (distance_factor ** 1.2)
                if distance_factor < 0.2:
                    adaptive_duration = 0.15 + 0.15 * distance_factor
                
                return {
                    "action": "move_left",
                    "intensity": min(intensity, self.cfg.max_intensity),
                    "note": "stable_left_tracking",
                    "action_type": 1,
                    "duration_factor": adaptive_duration,
                    "counter_strafe": adaptive_duration / self.cfg.stable_left_division
                }
            else:  # Move right (Action 2)
                intensity = abs(direction) * self.cfg.stable_right_multiplier * self.cfg.pixel_scaling
                adaptive_duration = 0.5 + 0.5 * (distance_factor ** 1.2)
                if distance_factor < 0.2:
                    adaptive_duration = 0.15 + 0.15 * distance_factor
                    
                return {
                    "action": "move_right",
                    "intensity": min(intensity, self.cfg.max_intensity),
                    "note": "stable_right_tracking",
                    "action_type": 2,
                    "duration_factor": adaptive_duration,
                    "counter_strafe": adaptive_duration / self.cfg.stable_right_division
                }
                
        else:  # abs(direction) > deadzone2
            # AHK Action 5 & 6: Unstable/aggressive tracking
            if direction > 0:  # Move left aggressively (Action 5)
                # Calculate max duration based on Control stat (AHK style)
                min_duration = 0.01
                # Use a base duration that scales with distance and control
                base_duration = abs(direction) * 2.0  # Scale up for visible differences
                if self.cfg.control >= 0.25:
                    max_duration = base_duration * 0.75
                elif self.cfg.control >= 0.2:
                    max_duration = base_duration * 0.8
                elif self.cfg.control >= 0.15:
                    max_duration = base_duration * 0.88
                else:
                    max_duration = base_duration + (abs(direction) * 0.2)
                
                raw_duration = abs(direction) * self.cfg.unstable_left_multiplier * self.cfg.pixel_scaling
                duration = max(min_duration, min(raw_duration, max_duration))
                
                return {
                    "action": "move_left",
                    "intensity": min(1.0, raw_duration),
                    "note": "unstable_left_aggressive", 
                    "action_type": 5,
                    "duration_factor": duration,
                    "counter_strafe": duration / self.cfg.unstable_left_division
                }
            else:  # Move right aggressively (Action 6)
                # Calculate max duration based on Control stat (AHK style)
                min_duration = 0.01
                # Use a base duration that scales with distance and control
                base_duration = abs(direction) * 2.0  # Scale up for visible differences
                if self.cfg.control >= 0.25:
                    max_duration = base_duration * 0.75
                elif self.cfg.control >= 0.2:
                    max_duration = base_duration * 0.8
                elif self.cfg.control >= 0.15:
                    max_duration = base_duration * 0.88
                else:
                    max_duration = base_duration + (abs(direction) * 0.2)
                    
                raw_duration = abs(direction) * self.cfg.unstable_right_multiplier * self.cfg.pixel_scaling
                duration = max(min_duration, min(raw_duration, max_duration))
                
                return {
                    "action": "move_right",
                    "intensity": min(1.0, raw_duration),
                    "note": "unstable_right_aggressive",
                    "action_type": 6,
                    "duration_factor": duration,
                    "counter_strafe": duration / self.cfg.unstable_right_division
                }


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
