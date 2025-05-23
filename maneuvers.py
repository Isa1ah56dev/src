from rlbot.agents.base_agent import SimpleControllerState # For defining controls in ControlStep
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection

from util.sequence import Sequence, ControlStep

# We pass the agent object to maneuvers if they need to, for example, send quick chats
# or access agent-specific data (though try to keep maneuvers self-contained if possible).

def perform_front_flip(agent):
    """
    Returns a Sequence object for a front flip.
    The agent object is passed in case the maneuver needs to send a quick chat or similar.
    """
    agent.send_quick_chat(team_only=False, quick_chat=QuickChatSelection.Information_IGotIt)

    return Sequence([
        ControlStep(duration=0.05, controls=SimpleControllerState(jump=True, pitch=0)), # Initial jump, ensure pitch is neutral
        ControlStep(duration=0.05, controls=SimpleControllerState(jump=False, pitch=0)),# Release jump
        ControlStep(duration=0.2, controls=SimpleControllerState(jump=True, pitch=-1)), # Second jump with forward pitch
        ControlStep(duration=0.8, controls=SimpleControllerState(pitch=0)), # Recovery, allow car to settle, neutral pitch
    ])

def perform_no_op(duration=0.1):
    """Returns a sequence that does nothing for a specified duration."""
    return Sequence([
        ControlStep(duration=duration, controls=SimpleControllerState())
    ])

# --- Add more maneuvers here ---
# e.g., perform_wavedash_forward(agent), perform_half_flip(agent), etc.

# Example: A simple sequence to drive forward and boost
def drive_forward_boost(duration=1.0):
    return Sequence([
        ControlStep(duration=duration, controls=SimpleControllerState(throttle=1.0, boost=True))
    ])

# Example: A simple turn
def turn_left_hard(duration=0.5):
    return Sequence([
        ControlStep(duration=duration, controls=SimpleControllerState(throttle=0.5, steer=-1.0, handbrake=True)) # Gentle throttle with handbrake
    ])
