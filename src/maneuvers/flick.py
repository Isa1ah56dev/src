from rlbot.agents.base_agent import SimpleControllerState
from util.sequence import Sequence, ControlStep

def perform_flick(agent, flick_type='forward'):
    """
    Returns a Sequence for different types of flicks.
    Types: 'forward', 'diagonal_right', 'diagonal_left', '45_right', '45_left'
    """
    if flick_type == 'forward':
        return Sequence([
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=True)),
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=False)),
            ControlStep(duration=0.1, controls=SimpleControllerState(jump=True, pitch=-1)),
            ControlStep(duration=0.7, controls=SimpleControllerState())
        ])
    elif flick_type.startswith('diagonal'):
        right = flick_type.endswith('right')
        return Sequence([
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=True)),
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=False)),
            ControlStep(duration=0.1, controls=SimpleControllerState(
                jump=True, 
                pitch=-1,
                roll=1 if right else -1
            )),
            ControlStep(duration=0.7, controls=SimpleControllerState())
        ])
    elif flick_type.startswith('45'):
        right = flick_type.endswith('right')
        return Sequence([
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=True)),
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=False)),
            ControlStep(duration=0.1, controls=SimpleControllerState(
                jump=True,
                pitch=-0.7,
                yaw=1 if right else -1
            )),
            ControlStep(duration=0.7, controls=SimpleControllerState())
        ])
    # Default to forward flick if type not recognized
    return perform_flick(agent, 'forward')
