from rlbot.agents.base_agent import SimpleControllerState
from util.sequence import Sequence, ControlStep
from util.vec import Vec3

def perform_basic_aerial(agent, target_location, duration=1.0):
    """
    Simple aerial: jump, boost, and point car at target_location.
    This is a placeholder for a more advanced aerial routine.
    """
    car = agent.get_output_packet().game_cars[agent.index]
    car_loc = Vec3(car.physics.location)
    direction = (target_location - car_loc).normalized()
    pitch = -1.0 if direction.z > 0.2 else 0.0
    yaw = direction.y / max(abs(direction.x) + abs(direction.y), 1e-5)
    return Sequence([
        ControlStep(duration=0.08, controls=SimpleControllerState(jump=True, boost=True, pitch=pitch, yaw=yaw)),
        ControlStep(duration=0.08, controls=SimpleControllerState(jump=False, boost=True, pitch=pitch, yaw=yaw)),
        ControlStep(duration=duration, controls=SimpleControllerState(boost=True, pitch=pitch, yaw=yaw)),
        ControlStep(duration=0.2, controls=SimpleControllerState()),
    ])
