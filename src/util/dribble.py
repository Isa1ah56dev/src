from rlbot.agents.base_agent import SimpleControllerState
from util.ball_control import get_ball_state, get_dribble_state
from util.vec import Vec3
import maneuvers

class DribbleController:
    def __init__(self, agent):
        self.agent = agent
        self.last_flick_time = 0
        self.dribble_started = False
        self.last_catch_attempt = 0
        self.MIN_FLICK_INTERVAL = 2.0  # Minimum seconds between flicks
        
    def execute(self, packet):
        """
        Main dribble control function. Returns SimpleControllerState.
        If a sequence is needed, it sets the agent's active_sequence and returns its tick.
        """
        current_time = packet.game_info.seconds_elapsed
        ball_state = get_ball_state(packet, self.agent.index)
        dribble_state = get_dribble_state(ball_state)

        # If we're already in a sequence, use that
        if self.agent.active_sequence is not None:
            controls = self.agent.active_sequence.tick(packet)
            if controls is not None:
                return controls
            self.agent.active_sequence = None

        # If we don't have the ball, try to catch it
        if not ball_state['on_roof'] and current_time - self.last_catch_attempt > 0.5:
            self.last_catch_attempt = current_time
            if ball_state['distance'] < 300 and ball_state['relative_velocity'].z < 0:
                self.agent.active_sequence = maneuvers.perform_catch(self.agent, ball_state)
                return self.agent.active_sequence.tick(packet)

        # If we have the ball, maintain control
        if ball_state['on_roof']:
            if not self.dribble_started:
                self.dribble_started = True

            # Check if we should flick
            if self.should_flick(packet, ball_state):
                self.last_flick_time = current_time
                self.agent.active_sequence = self.choose_flick(packet, ball_state)
                return self.agent.active_sequence.tick(packet)

            # Otherwise maintain dribble
            return self.maintain_dribble(dribble_state)

        self.dribble_started = False
        return None  # Let normal control take over
    
    def should_flick(self, packet, ball_state):
        """Determines if we should attempt a flick."""
        current_time = packet.game_info.seconds_elapsed
        if current_time - self.last_flick_time < self.MIN_FLICK_INTERVAL:
            return False
            
        # Check if opponent is close and we should flick
        for i in range(packet.num_cars):
            if i != self.agent.index and packet.game_cars[i].team != self.agent.team:
                opponent_loc = Vec3(packet.game_cars[i].physics.location)
                if opponent_loc.dist(ball_state['ball_loc']) < 1000:
                    return True
        
        return False
    
    def choose_flick(self, packet, ball_state):
        """Chooses the best flick type for the situation."""
        ball_loc = ball_state['ball_loc']
        car_loc = ball_state['car_loc']
        
        # Get opponent goal location
        opponent_goal = Vec3(0, 5120 if self.agent.team == 0 else -5120, 0)
        
        # Calculate angle to goal
        to_goal = (opponent_goal - car_loc).normalized()
        car_forward = self.agent.get_car_forward_vector(packet)
        angle = car_forward.ang_to(to_goal)
        
        if abs(angle) < 0.2:  # Fairly straight on
            return maneuvers.perform_flick(self.agent, 'forward')
        elif angle > 0:
            return maneuvers.perform_flick(self.agent, '45_right')
        else:
            return maneuvers.perform_flick(self.agent, '45_left')
    
    def maintain_dribble(self, dribble_state):
        """Returns controls to maintain a stable dribble."""
        controls = SimpleControllerState()
        
        if dribble_state['needs_slow']:
            controls.throttle = 0.3
        elif dribble_state['needs_boost']:
            controls.throttle = 1.0
            controls.boost = True
        else:
            controls.throttle = 0.6
        
        if dribble_state['needs_turn']:
            controls.steer = dribble_state['turn_amount']
            
        return controls
