from rlbot.agents.base_agent import SimpleControllerState
from util.sequence import Sequence, ControlStep

def perform_no_op(duration=0.1):
    """Returns a sequence that does nothing for a specified duration."""
    return Sequence([
        ControlStep(duration=duration, controls=SimpleControllerState())
    ])
