from rlbot.agents.base_agent import SimpleControllerState
from util.sequence import Sequence, ControlStep

def perform_momentum_turn(agent, turn_direction, keep_speed=True):
    """
    Returns a Sequence for maintaining momentum while turning.
    Uses powerslide for sharp turns while maintaining speed.
    """
    return Sequence([
        ControlStep(duration=0.2, controls=SimpleControllerState(
            throttle=1.0 if keep_speed else 0.5,
            steer=turn_direction,
            handbrake=abs(turn_direction) > 0.5
        )),
        ControlStep(duration=0.1, controls=SimpleControllerState(
            throttle=1.0,
            steer=turn_direction * 0.5
        ))
    ])
