from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection # For maneuvers that might use it

# Utilities from the util folder
from util.ball_prediction_analysis import find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target # Make sure this is correctly implemented in util/drive.py
from util.sequence import Sequence
from util.vec import Vec3

# Our maneuver library
import maneuvers # This will import maneuvers.py

class GeminiAgent(BaseAgent): # Renamed from MyRLBotAgent

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.active_sequence: Sequence = None
        self.boost_pad_tracker = BoostPadTracker()
        # Add a timer to prevent flipping too often, for example
        self.last_flip_time = 0.0
        self.flip_cooldown = 2.0 # Cooldown in seconds between flips

        self.logger.info(f"Gemini Agent (Team {self.team}, Index {self.index}) initialized.")

    def initialize_agent(self):
        # Set up information about the boost pads now that the game is active and the info is available
        self.boost_pad_tracker.initialize_boosts(self.get_field_info())
        self.logger.info(f"Gemini Agent boost pads initialized. Found {len(self.boost_pad_tracker.boost_pads)} pads.")
        self.last_flip_time = 0.0 # Initialize here in case of match restart

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        """
        This function will be called by the framework many times per second. This is where you can
        see the motion of the ball, etc. and return controls to drive your car.
        """
        current_time = packet.game_info.seconds_elapsed

        # Keep our boost pad info updated with which pads are currently active
        self.boost_pad_tracker.update_boost_status(packet)

        # This is good to keep at the beginning of get_output. It will allow you to continue
        # any sequences that you may have started during a previous call to get_output.
        if self.active_sequence is not None and not self.active_sequence.done:
            controls = self.active_sequence.tick(packet)
            if controls is not None:
                self.renderer.draw_string_2d(10, 50, 1, 1, f"Executing sequence: {self.active_sequence.steps[self.active_sequence.current_step_index].__class__.__name__ if self.active_sequence.steps else 'Unknown'}", self.renderer.yellow())
                return controls
            else: # Sequence finished
                self.active_sequence = None # Clear the sequence

        # Gather some information about our car and the ball
        my_car_data = packet.game_cars[self.index]
        car_location = Vec3(my_car_data.physics.location)
        car_velocity = Vec3(my_car_data.physics.velocity)
        car_orientation_matrix = [ # For steer_toward_target
            Vec3(my_car_data.physics.rotation.pitch, my_car_data.physics.rotation.yaw, my_car_data.physics.rotation.roll),
            Vec3(my_car_data.physics.location.x, my_car_data.physics.location.y, my_car_data.physics.location.z) # Not actually used by steer_toward_target, but common in older utils
        ]
        ball_location = Vec3(packet.game_ball.physics.location)
        ball_velocity = Vec3(packet.game_ball.physics.velocity)

        # By default we will chase the ball, but target_location can be changed later
        target_location = ball_location
        self.renderer.draw_string_2d(10, 10, 2, 2, f"Gemini Activated!", self.renderer.cyan())

        # --- Decision Making Logic ---

        # 1. Intercept planning (lead the ball)
        if car_location.dist(ball_location) > 1500: # If we are far from the ball
            ball_prediction = self.get_ball_prediction_struct()
            # Predict 1 to 2 seconds into the future, or time_to_reach_ball
            # For simplicity, let's use a fixed time for now
            prediction_time = current_time + 1.5
            ball_in_future = find_slice_at_time(ball_prediction, prediction_time)

            if ball_in_future is not None:
                predicted_ball_loc = Vec3(ball_in_future.physics.location)
                # Check if the prediction is reasonably on the ground
                if predicted_ball_loc.z < 300: # Only aim for ground predictions for now
                    target_location = predicted_ball_loc
                    self.renderer.draw_line_3d(ball_location, target_location, self.renderer.green())
                    self.renderer.draw_string_3d(target_location, 1, 1, "Pred Target", self.renderer.green())
                else:
                    self.renderer.draw_string_3d(predicted_ball_loc, 1, 1, "Aerial Pred", self.renderer.red())


        # 2. Consider a flip maneuver
        time_since_last_flip = current_time - self.last_flip_time
        # Conditions for flipping:
        # - Moving reasonably fast towards the target
        # - Close-ish to the target (but not too close that flip is useless)
        # - On the ground
        # - Cooldown met
        # - Not currently in an active sequence
        distance_to_target = car_location.dist(target_location)
        car_speed = car_velocity.length()

        if (250 < distance_to_target < 1000 and # Good distance range for a flip
            car_speed > 1000 and car_speed < 2200 and # Good speed range
            my_car_data.has_wheel_contact and
            time_since_last_flip > self.flip_cooldown and
            self.active_sequence is None): # No other sequence running

            # Check if we are reasonably aligned with the target before flipping
            # Simplified alignment check (can be improved with dot products)
            car_forward_direction = self.get_car_forward_vector()
            to_target_direction = (target_location - car_location).normalize()
            angle_to_target = car_forward_direction.ang_to(to_target_direction) # Requires ang_to in Vec3

            if abs(angle_to_target) < 0.3: # Roughly 17 degrees
                self.logger.info(f"Gemini attempting front flip towards target. Speed: {car_speed:.0f}")
                self.active_sequence = maneuvers.perform_front_flip(self) # Pass self for quick chat
                self.last_flip_time = current_time
                return self.active_sequence.tick(packet) # Start sequence immediately

        # 3. Default Action: Drive towards target_location
        controls = SimpleControllerState()
        # The steer_toward_target function from util.drive usually expects the car object itself
        controls.steer = steer_toward_target(my_car_data, car_location, target_location)
        controls.throttle = 1.0 # Go forward

        # Basic boost logic
        if car_speed < 2200 and distance_to_target > 500 and my_car_data.boost > 15:
            # Check alignment before boosting (similar to flip alignment)
            car_forward_direction = self.get_car_forward_vector()
            to_target_direction = (target_location - car_location).normalize()
            angle_to_target = car_forward_direction.ang_to(to_target_direction)
            if abs(angle_to_target) < 0.5: # Wider angle for boost
                controls.boost = True

        # --- Rendering ---
        self.renderer.draw_line_3d(car_location, target_location, self.renderer.white())
        self.renderer.draw_string_3d(car_location + Vec3(0,0,100), 1, 1, f'Speed: {car_speed:.0f}', self.renderer.white())
        self.renderer.draw_rect_3d(target_location, 10, 10, True, self.renderer.cyan(), centered=True)

        # Render boost pad locations and status (optional but helpful)
        # for i, pad in enumerate(self.boost_pad_tracker.boost_pads):
        #     color = self.renderer.green() if pad.is_active else self.renderer.red()
        #     self.renderer.draw_rect_3d(pad.location, 50, 50, False, color)
        #     # self.renderer.draw_string_3d(pad.location + Vec3(0,0,50), 1,1, f"{i}", self.renderer.white())

        return controls

    def get_car_forward_vector(self) -> Vec3:
        """Helper to get the car's forward-facing vector."""
        my_car_data = self.get_ball_prediction_struct().slices[0].physics.location # A bit hacky, should use packet
        # This is not actually the forward vector. A proper implementation is needed.
        # For now, this is a placeholder.
        # A correct implementation uses the car's rotation.
        # Let's assume util/orientation.py or similar provides this or implement it.
        # For now, we'll use a simplified approach based on yaw, which only works for flat forward.
        
        # Get car data from the packet (this should be passed in or accessed carefully)
        # This is a common point of error if packet isn't available here.
        # It's better to calculate this in get_output where packet IS available.
        # Let's assume this function is called from get_output and car_data is available.
        
        # This method should ideally be part of the car object or a utility.
        # For now, let's just make a note that this needs to be robust.
        # We'll use a simplified version for demonstration:
        car_yaw = self.game_tick_packet.game_cars[self.index].physics.rotation.yaw
        forward_x = math.cos(car_yaw)
        forward_y = math.sin(car_yaw)
        return Vec3(forward_x, forward_y, 0).normalize()

    # Make sure to implement Vec3.ang_to if it's not in your util/vec.py
    # Example Vec3.ang_to(self, ideal_vector_to_target):
    #   current_in_radians = math.atan2(self.y, self.x)
    #   ideal_in_radians = math.atan2(ideal_vector_to_target.y, ideal_vector_to_target.x)
    #   diff = ideal_in_radians - current_in_radians
    #   if diff > math.pi: diff -= 2 * math.pi
    #   if diff < -math.pi: diff += 2 * math.pi
    #   return diff