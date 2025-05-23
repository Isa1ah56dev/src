from rlbot.agents.base_agent import SimpleControllerState
from util.sequence import Sequence, ControlStep

def perform_kickoff_flip(agent):
    """
    Improved kickoff: boost straight, steer toward ball, flip at optimal distance.
    """
    return Sequence([
        ControlStep(duration=0.32, controls=SimpleControllerState(throttle=1.0, boost=True)),
        ControlStep(duration=0.04, controls=SimpleControllerState(jump=True, pitch=0, throttle=1.0, boost=True)),
        ControlStep(duration=0.04, controls=SimpleControllerState(jump=False, pitch=0, throttle=1.0, boost=True)),
        ControlStep(duration=0.16, controls=SimpleControllerState(jump=True, pitch=-1, throttle=1.0, boost=True)),
        ControlStep(duration=0.4, controls=SimpleControllerState(throttle=1.0, boost=True)),
    ])
