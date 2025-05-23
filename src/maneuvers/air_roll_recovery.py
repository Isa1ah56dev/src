from rlbot.agents.base_agent import SimpleControllerState
from util.sequence import Sequence, ControlStep

def perform_air_roll_recovery(agent):
    """
    Returns a Sequence object for a basic air roll recovery (wheels down).
    """
    return Sequence([
        ControlStep(duration=0.5, controls=SimpleControllerState(roll=1.0)),
        ControlStep(duration=0.5, controls=SimpleControllerState(roll=-1.0)),
    ])
