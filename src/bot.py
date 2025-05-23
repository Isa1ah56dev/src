from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection # For maneuvers that might use it

# Utilities from the util folder
from util.ball_prediction_analysis import find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target # Make sure this is correctly implemented in util/drive.py
from util.sequence import Sequence
from util.vec import Vec3
from util.dribble import DribbleController  # Add the new dribble controller
from util.ball_predictor import find_next_ground_touch, find_best_intercept, find_shot_opportunity
from util.decision import decide_action, BotDecision
from util.position_predictor import PositionPredictor

# Our maneuver library
from maneuvers.half_flip import perform_half_flip
from maneuvers.front_flip import perform_front_flip
from maneuvers.basic_aerial import perform_basic_aerial
from maneuvers.kickoff import perform_kickoff_flip
from maneuvers.catch import perform_catch
from maneuvers.flick import perform_flick
from maneuvers.momentum_turn import perform_momentum_turn
from maneuvers.no_op import perform_no_op
from maneuvers.turtle_recovery import perform_turtle_recovery
from maneuvers.air_roll_recovery import perform_air_roll_recovery

import math

def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))

class GeminiAgent(BaseAgent): # Renamed from MyRLBotAgent

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.active_sequence: Sequence = None
        self.boost_pad_tracker = BoostPadTracker()
        self.dribble_controller = DribbleController(self)  # Initialize dribble controller
        # Add a timer to prevent flipping too often, for example
        self.last_flip_time = 0.0
        self.flip_cooldown = 2.0 # Cooldown in seconds between flips

        self.logger.info(f"Gemini Agent (Team {self.team}, Index {self.index}) initialized.")

    def initialize_agent(self):
        # Set up information about the boost pads now that the game is active and the info is available
        self.boost_pad_tracker.initialize_boosts(self.get_field_info())
        self.logger.info(f"Gemini Agent boost pads initialized. Found {len(self.boost_pad_tracker.boost_pads)} pads.")
        self.last_flip_time = 0.0 # Initialize here in case of match restart

    # --- State Machine for Platinum-Level Logic ---
    class BotState:
        ATTACK_GROUND = 'attack_ground'
        ATTACK_AERIAL = 'attack_aerial'
        DRIBBLE = 'dribble'
        WALL_PLAY = 'wall_play'
        REBOUND = 'rebound'
        DEFEND_GOAL = 'defend_goal'
        DEFEND_CLEAR = 'defend_clear'
        SHADOW = 'shadow'
        CHALLENGE = 'challenge'
        GET_BOOST = 'get_boost'
        ROTATE = 'rotate'
        NONE = 'none'

    def select_state(self, packet, car_location, car_velocity, ball_location, ball_velocity, my_goal, opponent_goal):
        """
        Determines the bot's high-level state based on field context.
        """
        # Use ball prediction for intercepts
        ball_prediction = self.get_ball_prediction_struct()
        intercept_slice = find_best_intercept(car_location, car_velocity.length(), ball_prediction)
        dist_to_ball = car_location.dist(ball_location)
        dist_ball_to_my_goal = ball_location.dist(my_goal)
        dist_ball_to_opponent_goal = ball_location.dist(opponent_goal)
        my_car_data = packet.game_cars[self.index]
        boost = my_car_data.boost
        # Defensive states
        if dist_ball_to_my_goal < 1200 and dist_to_ball > 600:
            return self.BotState.DEFEND_GOAL
        if dist_ball_to_my_goal < 2500 and dist_to_ball < 900:
            return self.BotState.DEFEND_CLEAR
        # Shadowing
        if dist_ball_to_my_goal < 3000 and dist_to_ball < 1800 and ball_velocity.length() < 700:
            return self.BotState.SHADOW
        # Challenge
        if dist_to_ball < 900 and abs(ball_location.z) < 200:
            return self.BotState.CHALLENGE
        # Attacking states
        if ball_location.z > 350 and boost > 20 and dist_to_ball < 1800:
            return self.BotState.ATTACK_AERIAL
        if dist_ball_to_opponent_goal < 2000 and dist_to_ball < 900:
            return self.BotState.ATTACK_GROUND
        # Dribble
        if abs(ball_location.z - car_location.z) < 120 and dist_to_ball < 350 and ball_velocity.length() < 600:
            return self.BotState.DRIBBLE
        # Wall play
        if abs(ball_location.y) > 4000 and ball_location.z > 200:
            return self.BotState.WALL_PLAY
        # Rebound
        if ball_location.z > 300 and abs(ball_location.y) > 3000:
            return self.BotState.REBOUND
        # Get boost
        if boost < 20 and dist_to_ball > 1200:
            return self.BotState.GET_BOOST
        # Default
        return self.BotState.ROTATE

    # --- Platinum-Level Aerial System ---
    class AerialState:
        IDLE = 0
        PREPARING = 1
        TAKING_OFF = 2
        FLIGHT = 3
        RECOVERY = 4

    def should_attempt_platinum_aerial(self, packet, car_location, car_velocity, car_orientation, my_car_data, ball_prediction, current_time, my_goal, opponent_goal):
        """
        Decide if a Platinum-level aerial is appropriate, following the user's breakdown.
        Returns (intercept_point, intercept_time) if possible, else (None, None).
        """
        best_intercept = None
        best_time = None
        for i in range(ball_prediction.num_slices):
            slice = ball_prediction.slices[i]
            t = slice.game_seconds - current_time
            if t < 0.5 or t > 3.0:
                continue
            ball_pos = Vec3(slice.physics.location)
            ball_vel = Vec3(slice.physics.velocity)
            # Only consider balls at a Platinum aerial height and not too fast horizontally
            if 300 < ball_pos.z < 1000 and ball_vel.flat().length() < 1800:
                # Estimate time to reach (simplified: distance / average aerial speed)
                dist = car_location.dist(ball_pos)
                avg_aerial_speed = 1300  # Platinum-level
                time_to_reach = dist / avg_aerial_speed
                # Estimate boost needed (simplified: 33 units/sec vertical, 1 boost = 33 units)
                height_needed = ball_pos.z - car_location.z
                boost_needed = max(0, height_needed / 33)
                if abs(time_to_reach - t) < 0.35 and my_car_data.boost > boost_needed + 10:
                    # Check if it's a shot or clear opportunity
                    is_offense = (ball_pos - opponent_goal).length() < (ball_pos - my_goal).length()
                    is_defense = (ball_pos - my_goal).length() < 2000
                    if is_offense or is_defense:
                        best_intercept = ball_pos
                        best_time = t
                        break
        return best_intercept, best_time

    def perform_platinum_aerial(self, packet, car_location, car_velocity, car_orientation, my_car_data, intercept_point, intercept_time):
        """
        Executes a Platinum-level aerial using a state machine and proportional controller.
        """
        # State variables
        if not hasattr(self, 'aerial_state'):
            self.aerial_state = self.AerialState.IDLE
            self.aerial_timer = 0.0
            self.aerial_takeoff_spot = None
            self.aerial_jump_time = 0.0
            self.aerial_has_jumped = False
            self.aerial_has_double_jumped = False
        controls = SimpleControllerState()
        current_time = packet.game_info.seconds_elapsed
        # Reset aerial state if bot is on ground after an aerial attempt
        if my_car_data.has_wheel_contact and self.aerial_state != self.AerialState.IDLE:
            self.aerial_state = self.AerialState.IDLE
            self.aerial_has_jumped = False
            self.aerial_has_double_jumped = False
        # --- Approach & Alignment (PREPARING) ---
        if self.aerial_state == self.AerialState.IDLE:
            # Drive to takeoff spot (under or slightly ahead of intercept)
            takeoff_spot = Vec3(intercept_point.x, intercept_point.y, 0)
            self.aerial_takeoff_spot = takeoff_spot
            dist = car_location.flat().dist(takeoff_spot.flat())
            if dist > 120:
                controls.throttle = 1.0
                controls.steer = clamp(steer_toward_target(my_car_data, takeoff_spot), -1.0, 1.0)
                controls.boost = False
                # Platinum nuance: alignment might not be perfect
                return controls
            else:
                self.aerial_state = self.AerialState.PREPARING
                self.aerial_timer = current_time
        if self.aerial_state == self.AerialState.PREPARING:
            # Jump just before reaching takeoff spot
            controls.jump = True
            self.aerial_jump_time = current_time
            self.aerial_state = self.AerialState.TAKING_OFF
            return controls
        if self.aerial_state == self.AerialState.TAKING_OFF:
            # After jump, pitch back and start boosting
            jump_duration = current_time - self.aerial_jump_time
            if jump_duration < 0.12:
                controls.jump = True
                controls.pitch = -1.0
                controls.boost = False
                return controls
            else:
                controls.jump = False
                controls.pitch = -1.0
                controls.boost = True
                # Optionally, slow double jump for extra height (Platinum nuance: not always optimal)
                if not self.aerial_has_double_jumped and jump_duration > 0.18 and jump_duration < 0.32:
                    controls.jump = True
                    self.aerial_has_double_jumped = True
                if jump_duration > 0.32:
                    self.aerial_state = self.AerialState.FLIGHT
            return controls
        if self.aerial_state == self.AerialState.FLIGHT:
            # In-air flight & correction
            to_target = (intercept_point - car_location).normalized()
            forward = car_orientation.forward
            error = to_target - forward
            # Proportional controller for pitch/yaw (Platinum: wobbly, not perfect)
            controls.pitch = clamp(error.z * 2, -1, 1)
            controls.yaw = clamp(error.y * 2, -1, 1)
            controls.boost = True
            # Minimal/no air roll
            # Feather boost as bot gets close
            if car_location.dist(intercept_point) < 200:
                controls.boost = False
            # Contact: try to hit with nose/corners
            if car_location.dist(intercept_point) < 120:
                # Optionally, use dodge for extra power (Platinum: timing can be off)
                if not self.aerial_has_jumped:
                    controls.jump = True
                    self.aerial_has_jumped = True
                else:
                    controls.jump = False
                self.aerial_state = self.AerialState.RECOVERY
            return controls
        if self.aerial_state == self.AerialState.RECOVERY:
            # After contact, stop boosting, orient for landing
            controls.boost = False
            controls.pitch = 0
            controls.yaw = 0
            controls.roll = 0
            # Try to land on wheels (Platinum: landings can be messy)
            if car_location.z < 50:
                self.aerial_state = self.AerialState.IDLE
                self.aerial_has_jumped = False
                self.aerial_has_double_jumped = False
            return controls
        return controls

    def execute_state(self, state, packet, car_location, car_velocity, ball_location, ball_velocity, my_goal, opponent_goal, my_car_data):
        controls = SimpleControllerState()
        # --- Attacking ---
        if state == self.BotState.ATTACK_GROUND:
            # Power shot logic: line up, accelerate, flip into ball
            target = opponent_goal
            to_ball = (ball_location - car_location).normalized()
            to_goal = (target - ball_location).normalized()
            alignment = to_ball.dot(to_goal)
            if alignment > 0.7 and car_location.dist(ball_location) < 300:
                # Close and lined up: flip for power shot
                if self.active_sequence is None:
                    self.active_sequence = perform_front_flip(self)
                    return self.active_sequence.tick(packet)
            # Otherwise, drive to line up
            controls.throttle = 1.0
            controls.steer = clamp(steer_toward_target(my_car_data, ball_location), -1.0, 1.0)
            return controls
        if state == self.BotState.ATTACK_AERIAL:
            # --- Platinum-level aerial logic ---
            ball_prediction = self.get_ball_prediction_struct()
            from util.orientation import Orientation
            car_orientation = Orientation(my_car_data.physics.rotation)
            current_time = packet.game_info.seconds_elapsed
            intercept_point, intercept_time = self.should_attempt_platinum_aerial(
                packet, car_location, car_velocity, car_orientation, my_car_data, ball_prediction, current_time, my_goal, opponent_goal)
            if intercept_point is not None:
                # Always attempt a jump if a valid intercept is found
                return self.perform_platinum_aerial(packet, car_location, car_velocity, car_orientation, my_car_data, intercept_point, intercept_time)
            # If not a good aerial, fallback to default (drive towards ball)
            controls.throttle = 1.0
            controls.steer = clamp(steer_toward_target(my_car_data, ball_location), -1.0, 1.0)
            return controls
        if state == self.BotState.DRIBBLE:
            # Use dribble controller
            controls = self.dribble_controller.execute(packet)
            if isinstance(controls, SimpleControllerState):
                return controls
            elif isinstance(controls, Sequence):
                self.active_sequence = controls
                return self.active_sequence.tick(packet)
        if state == self.BotState.WALL_PLAY:
            # --- Wall jump logic for Platinum ---
            # If the bot is on the wall and the ball is high, jump and boost off the wall
            if not my_car_data.has_wheel_contact and abs(car_location.z) > 200:
                controls.jump = True
                controls.boost = True
                # Aim nose toward ball
                to_ball = (ball_location - car_location).normalized()
                from util.orientation import Orientation
                car_orientation = Orientation(my_car_data.physics.rotation)
                forward = car_orientation.forward
                error = to_ball - forward
                controls.pitch = clamp(error.z * 2, -1, 1)
                controls.yaw = clamp(error.y * 2, -1, 1)
                return controls
            # Otherwise, drive up the wall toward the ball
            controls.throttle = 1.0
            controls.steer = clamp(steer_toward_target(my_car_data, ball_location), -1.0, 1.0)
            return controls
        if state == self.BotState.REBOUND:
            # After shot, keep moving forward for follow-up
            controls.throttle = 1.0
            controls.steer = clamp(steer_toward_target(my_car_data, opponent_goal), -1.0, 1.0)
            return controls
        # --- Defending ---
        if state == self.BotState.DEFEND_GOAL:
            # Position in net, face ball, block shot
            goal_line = my_goal + (ball_location - my_goal).normalized() * 300
            controls.throttle = 1.0
            controls.steer = clamp(steer_toward_target(my_car_data, goal_line), -1.0, 1.0)
            # If ball is close, flip to save
            if car_location.dist(ball_location) < 350:
                if self.active_sequence is None:
                    self.active_sequence = perform_front_flip(self)
                    return self.active_sequence.tick(packet)
            return controls
        if state == self.BotState.DEFEND_CLEAR:
            # Hit ball hard and high towards side or upfield
            clear_target = opponent_goal + Vec3(1000 if car_location.x < 0 else -1000, 0, 0)
            controls.throttle = 1.0
            controls.steer = clamp(steer_toward_target(my_car_data, clear_target), -1.0, 1.0)
            if car_location.dist(ball_location) < 350:
                if self.active_sequence is None:
                    self.active_sequence = perform_front_flip(self)
                    return self.active_sequence.tick(packet)
            return controls
        if state == self.BotState.SHADOW:
            # Stay between ball and net, match speed, delay
            shadow_pos = my_goal + (ball_location - my_goal).normalized() * 800
            controls.throttle = 0.5
            controls.steer = clamp(steer_toward_target(my_car_data, shadow_pos), -1.0, 1.0)
            return controls
        if state == self.BotState.CHALLENGE:
            # Flip into ball for 50/50
            if self.active_sequence is None:
                self.active_sequence = perform_front_flip(self)
                return self.active_sequence.tick(packet)
            return controls
        if state == self.BotState.GET_BOOST:
            # Go for nearest boost pad
            best_pad = self.boost_pad_tracker.get_best_boost(car_location)
            if best_pad:
                controls.throttle = 1.0
                controls.steer = clamp(steer_toward_target(my_car_data, best_pad.location), -1.0, 1.0)
                return controls
        # --- Default/Rotation ---
        if state == self.BotState.ROTATE:
            # Rotate back post or cover midfield
            if self.team == 0:
                back_post = Vec3(-800, -5120, 0) if car_location.x < 0 else Vec3(800, -5120, 0)
            else:
                back_post = Vec3(-800, 5120, 0) if car_location.x < 0 else Vec3(800, 5120, 0)
            controls.throttle = 1.0
            controls.steer = clamp(steer_toward_target(my_car_data, back_post), -1.0, 1.0)
            return controls
        return controls

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        current_time = packet.game_info.seconds_elapsed
        self.boost_pad_tracker.update_boost_status(packet)
        controls = SimpleControllerState()

        my_car_data = packet.game_cars[self.index]
        car_location = Vec3(my_car_data.physics.location)
        car_velocity = Vec3(my_car_data.physics.velocity)
        ball_location = Vec3(packet.game_ball.physics.location)
        ball_velocity = Vec3(packet.game_ball.physics.velocity)

        from util.orientation import Orientation
        car_orientation = Orientation(my_car_data.physics.rotation)

        # Define goal locations
        if self.team == 0:
            my_goal = Vec3(0, -5120, 0)
            opponent_goal = Vec3(0, 5120, 0)
        else:
            my_goal = Vec3(0, 5120, 0)
            opponent_goal = Vec3(0, -5120, 0)

        # --- Platinum-Level State Machine ---
        state = self.select_state(packet, car_location, car_velocity, ball_location, ball_velocity, my_goal, opponent_goal)
        controls = self.execute_state(state, packet, car_location, car_velocity, ball_location, ball_velocity, my_goal, opponent_goal, my_car_data)
        if hasattr(controls, 'steer'):
            controls.steer = float(clamp(controls.steer, -1.0, 1.0))
        return controls

    def get_car_forward_vector(self, packet: GameTickPacket) -> Vec3:
        """Returns a Vec3 representing the forward direction of the car."""
        from util.orientation import Orientation
        my_car = packet.game_cars[self.index]
        car_orientation = Orientation(my_car.physics.rotation)
        return car_orientation.forward

    def handle_recovery(self, car_data, controls_to_modify: SimpleControllerState):
        from util.orientation import Orientation
        import math
        car_orientation = Orientation(car_data.physics.rotation)
        car_up = car_orientation.up
        car_forward = car_orientation.forward
        car_right = car_orientation.right
        car_velocity_vec = Vec3(car_data.physics.velocity)

        # If turtled (on roof), use jump+roll to try to flip over
        if car_up.z < -0.5: # Condition for being on the roof
            controls_to_modify.jump = True
            controls_to_modify.roll = 1.0 if car_right.z < 0 else -1.0 # Roll in the direction to flip over
            controls_to_modify.pitch = 0
            controls_to_modify.throttle = 0
            controls_to_modify.boost = False
            self.renderer.draw_string_2d(10, 80, 1, 1, "Turtle Recovery: Jump+Roll", self.renderer.red())
        # If airborne but not turtled, use roll and pitch to level out
        else:
            # --- Roll Control ---
            controls_to_modify.roll = 0
            if car_right.z > 0.15:
                controls_to_modify.roll = -1.0
            elif car_right.z < -0.15:
                controls_to_modify.roll = 1.0

            # --- Pitch Control ---
            controls_to_modify.pitch = 0
            flat_vel = car_velocity_vec.flat()
            if car_velocity_vec.length() > 300 and flat_vel.length() != 0:
                target_fwd_flat_velocity_z = flat_vel.normalized().z if hasattr(flat_vel.normalized(), 'z') else 0.0
                if car_forward.z > target_fwd_flat_velocity_z + 0.1:
                    controls_to_modify.pitch = 1.0
                elif car_forward.z < target_fwd_flat_velocity_z - 0.1:
                    controls_to_modify.pitch = -1.0
            else:
                if car_forward.z > 0.2:
                    controls_to_modify.pitch = 1.0
                elif car_forward.z < -0.1:
                    controls_to_modify.pitch = -1.0

            controls_to_modify.throttle = 0
            controls_to_modify.boost = False
            self.renderer.draw_string_2d(10, 70, 1, 1, f"Recovering: R{controls_to_modify.roll:.1f} P{controls_to_modify.pitch:.1f}", self.renderer.orange())

        return controls_to_modify # Always return controls if recovery is handled

    def attempt_airborne_leveling(self, car_data, controls_to_modify: SimpleControllerState):
        from util.orientation import Orientation
        import math
        car_orientation = Orientation(car_data.physics.rotation)
        car_up = car_orientation.up
        car_forward = car_orientation.forward
        car_right = car_orientation.right
        car_velocity_vec = Vec3(car_data.physics.velocity)

        # --- Roll Control (for airborne but not turtled) ---
        controls_to_modify.roll = 0
        if car_right.z > 0.15:
            controls_to_modify.roll = -1.0
        elif car_right.z < -0.15:
            controls_to_modify.roll = 1.0

        # --- Pitch Control (for airborne but not turtled) ---
        controls_to_modify.pitch = 0
        flat_vel = car_velocity_vec.flat()
        if car_velocity_vec.length() > 300 and flat_vel.length() != 0:
            target_fwd_flat_velocity_z = flat_vel.normalized().z if hasattr(flat_vel.normalized(), 'z') else 0.0
            if car_forward.z > target_fwd_flat_velocity_z + 0.1:
                controls_to_modify.pitch = 1.0
            elif car_forward.z < target_fwd_flat_velocity_z - 0.1:
                controls_to_modify.pitch = -1.0
        else:
            if car_forward.z > 0.2:
                controls_to_modify.pitch = 1.0
            elif car_forward.z < -0.1:
                controls_to_modify.pitch = -1.0

        controls_to_modify.throttle = 0
        controls_to_modify.boost = False
        self.renderer.draw_string_2d(10, 70, 1, 1, f"Recovering: R{controls_to_modify.roll:.1f} P{controls_to_modify.pitch:.1f}", self.renderer.orange())
        return controls_to_modify
