from util.vec import Vec3

class PositionPredictor:
    @staticmethod
    def predict_future_position(car_location, car_velocity, car_forward, car_angular_velocity, dt, use_forward_only=False):
        """
        Predicts the car's position after dt seconds.
        If use_forward_only is True, only considers forward velocity (ignores drift/sideways).
        Includes a simple angular velocity estimate for turning.
        """
        if use_forward_only:
            forward_speed = car_velocity.dot(car_forward)
            predicted = car_location + car_forward * (forward_speed * dt)
        else:
            predicted = car_location + car_velocity * dt
        # Optionally, add a simple turn prediction (not full physics)
        # This is a placeholder for more advanced turn prediction
        # You could rotate the forward vector by angular_velocity.z * dt
        return predicted

    @staticmethod
    def time_to_reach(car_location, car_velocity, target_location, max_speed=2300):
        """
        Estimates time to reach a target location, assuming constant velocity up to max_speed.
        """
        dist = car_location.dist(target_location)
        speed = min(car_velocity.length(), max_speed)
        if speed < 100:
            speed = 400  # Assume some acceleration from a stop
        return dist / speed

    @staticmethod
    def will_arrive_before(car_location, car_velocity, target_location, target_time, max_speed=2300):
        """
        Returns True if the car can reach the target location before target_time seconds.
        """
        t = PositionPredictor.time_to_reach(car_location, car_velocity, target_location, max_speed)
        return t < target_time
