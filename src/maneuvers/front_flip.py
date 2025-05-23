from rlbot.agents.base_agent import SimpleControllerState
from util.sequence import Sequence, ControlStep

def perform_front_flip(agent):
    """
    Returns a Sequence object for a front flip.
    """
    return Sequence([
        ControlStep(duration=0.05, controls=SimpleControllerState(jump=True, pitch=0)), # Initial jump
        ControlStep(duration=0.05, controls=SimpleControllerState(jump=False, pitch=0)),# Release jump
        ControlStep(duration=0.2, controls=SimpleControllerState(jump=True, pitch=-1)), # Second jump with forward pitch
        ControlStep(duration=0.8, controls=SimpleControllerState(pitch=0)), # Recovery
    ])
