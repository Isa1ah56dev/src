from rlbot.agents.base_agent import SimpleControllerState
from util.sequence import Sequence, ControlStep

def perform_turtle_recovery(agent):
    """
    Returns a Sequence object to help the bot flip off its roof.
    Uses a quick jump and roll, then sustained roll for recovery.
    """
    return Sequence([
        ControlStep(duration=0.1, controls=SimpleControllerState(jump=True, roll=1.0)), # Quick jump and roll
        ControlStep(duration=0.5, controls=SimpleControllerState(roll=1.0)), # Sustain roll
        ControlStep(duration=0.5, controls=SimpleControllerState()), # Recovery
    ])
