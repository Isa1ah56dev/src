from util.vec import Vec3
from rlbot.utils.structures.game_data_struct import GameTickPacket

def get_ball_state(packet: GameTickPacket, car_index: int):
    """
    Analyzes the ball's state relative to the car for dribbling decisions.
    Returns a dict with useful ball state information.
    """
    ball = packet.game_ball.physics
    car = packet.game_cars[car_index].physics
    
    ball_loc = Vec3(ball.location)
    car_loc = Vec3(car.location)
    ball_vel = Vec3(ball.velocity)
    car_vel = Vec3(car.velocity)
    
    relative_vel = ball_vel - car_vel
    distance = ball_loc.dist(car_loc)
    
    # Calculate if ball is on car roof
    ball_height = ball_loc.z - car_loc.z
    on_roof = 60 < ball_height < 200  # Approximate height range for dribbling
    
    return {
        'distance': distance,
        'relative_velocity': relative_vel,
        'height': ball_height,
        'on_roof': on_roof,
        'ball_loc': ball_loc,
        'car_loc': car_loc,
        'ball_vel': ball_vel,
        'car_vel': car_vel
    }

def get_dribble_state(ball_state):
    """
    Analyzes the current dribble quality and suggests corrections.
    Returns a dict with dribble state and suggested adjustments.
    """
    corrections = {
        'needs_catch': False,
        'needs_slow': False,
        'needs_boost': False,
        'needs_turn': False,
        'turn_amount': 0.0
    }
    
    rel_vel = ball_state['relative_velocity']
    distance = ball_state['distance']
    
    # Ball moving too fast relative to car
    if rel_vel.length() > 800:
        corrections['needs_slow'] = True
    
    # Ball getting away from car
    if distance > 200 and ball_state['on_roof']:
        corrections['needs_boost'] = True
    
    # Ball needs to be caught
    if not ball_state['on_roof'] and distance < 300:
        corrections['needs_catch'] = True
        
    # Calculate turning adjustment if ball is sliding sideways
    if ball_state['on_roof']:
        lateral_vel = abs(rel_vel.y)  # Assuming y is the lateral axis
        if lateral_vel > 100:
            corrections['needs_turn'] = True
            corrections['turn_amount'] = -rel_vel.y / 1000  # Normalized turning amount
    
    return corrections
