from rlbot.agents.base_agent import SimpleControllerState
from util.sequence import Sequence, ControlStep

def perform_catch(agent, ball_state):
    """
    Returns a Sequence for smoothly catching the ball on the car's roof.
    Uses ball state to determine optimal catch speed and angle.
    """
    rel_vel = ball_state['relative_velocity']
    distance = ball_state['distance']
    # Gentle catch if ball is coming down
    if rel_vel.z < -100 and distance < 200:
        return Sequence([
            ControlStep(duration=0.1, controls=SimpleControllerState(throttle=0.3)),
            ControlStep(duration=0.1, controls=SimpleControllerState(throttle=0.5))
        ])
    # Otherwise, maintain speed for momentum
    return Sequence([
        ControlStep(duration=0.2, controls=SimpleControllerState(throttle=1.0))
    ])
