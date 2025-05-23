from util.vec import Vec3
from util.ball_prediction_analysis import find_slice_at_time

# Helper to find the soonest ground touch in the ball prediction

def find_next_ground_touch(ball_prediction):
    for i in range(ball_prediction.num_slices):
        slice = ball_prediction.slices[i]
        if slice.physics.location.z < 150 and abs(slice.physics.velocity.z) < 100:
            return slice
    return None

# Helper to find the best intercept slice for a car

def find_best_intercept(car_location, car_speed, ball_prediction, max_time=3.0, min_height=0, max_height=300):
    best_slice = None
    best_time = None
    for i in range(ball_prediction.num_slices):
        slice = ball_prediction.slices[i]
        t = slice.game_seconds
        ball_loc = Vec3(slice.physics.location)
        if min_height <= ball_loc.z <= max_height:
            time_to_ball = t
            dist = car_location.dist(ball_loc)
            # Estimate time to reach ball (very simple, can be improved)
            time_needed = dist / max(car_speed, 400)
            if time_needed < (t - ball_prediction.slices[0].game_seconds) + 0.2:
                best_slice = slice
                best_time = t
                break
    return best_slice

# Helper to find a shot opportunity (ball moving toward opponent goal)
def find_shot_opportunity(ball_prediction, opponent_goal_y, min_speed=400):
    for i in range(ball_prediction.num_slices):
        slice = ball_prediction.slices[i]
        ball_loc = Vec3(slice.physics.location)
        ball_vel = Vec3(slice.physics.velocity)
        # Check if ball is moving toward opponent goal
        if (opponent_goal_y > 0 and ball_vel.y > min_speed) or (opponent_goal_y < 0 and ball_vel.y < -min_speed):
            if ball_loc.z < 300:
                return slice
    return None

def predict_car_position(car_location, car_velocity, car_forward, dt, use_forward_only=False):
    """
    Predicts the car's position after dt seconds.
    If use_forward_only is True, only considers forward velocity (ignores drift/sideways).
    """
    if use_forward_only:
        forward_speed = car_velocity.dot(car_forward)
        predicted = car_location + car_forward * (forward_speed * dt)
    else:
        predicted = car_location + car_velocity * dt
    return predicted
