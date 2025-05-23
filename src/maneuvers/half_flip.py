from rlbot.agents.base_agent import SimpleControllerState
from util.sequence import Sequence, ControlStep

def perform_half_flip(agent):
    """
    Returns a Sequence object for a half-flip (backflip, cancel, air roll recovery).
    """
    return Sequence([
        ControlStep(duration=0.08, controls=SimpleControllerState(jump=True, pitch=1.0, throttle=-1.0)),  # Backflip
        ControlStep(duration=0.10, controls=SimpleControllerState(jump=False, pitch=1.0, throttle=-1.0)), # Release jump
        ControlStep(duration=0.18, controls=SimpleControllerState(jump=False, pitch=-1.0, throttle=1.0, roll=1.0)), # Flip cancel + air roll
        ControlStep(duration=0.5, controls=SimpleControllerState()), # Recovery
    ])
