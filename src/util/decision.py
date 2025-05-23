from util.vec import Vec3

class BotDecision:
    ATTACK = 'attack'
    DEFEND = 'defend'
    INTERCEPT = 'intercept'
    CLEAR = 'clear'
    BOOST = 'boost'
    AERIAL = 'aerial'
    DRIBBLE = 'dribble'
    NONE = 'none'

def decide_action(agent, packet, car_location, car_velocity, car_forward, ball_location, ball_velocity, my_goal, opponent_goal):
    """
    Returns a string representing the bot's high-level action.
    """
    my_car = packet.game_cars[agent.index]
    boost = my_car.boost
    ball_to_my_goal = my_goal - ball_location
    ball_to_opponent_goal = opponent_goal - ball_location
    car_to_ball = ball_location - car_location
    dist_to_ball = car_location.dist(ball_location)
    dist_ball_to_my_goal = ball_location.dist(my_goal)
    dist_ball_to_opponent_goal = ball_location.dist(opponent_goal)
    
    # 1. Boost logic: If low on boost and not in immediate danger, go for boost
    if boost < 20 and dist_to_ball > 1200 and abs(car_to_ball.z) < 200:
        return BotDecision.BOOST
    
    # 2. Defend: If ball is close to our goal, prioritize defense
    if dist_ball_to_my_goal < 1800 and dist_to_ball > 600:
        return BotDecision.DEFEND
    
    # 3. Clear: If ball is in our half and we're behind it, clear
    if abs(ball_location.y) < 2000 and car_location.y * agent.team < 0 and dist_to_ball < 900:
        return BotDecision.CLEAR
    
    # 4. Intercept: If we can reach the ball before opponent, intercept
    if dist_to_ball < 1200 and abs(car_to_ball.z) < 200:
        return BotDecision.INTERCEPT
    
    # 5. Aerial: If ball is airborne and we have boost, and it's reachable
    if ball_location.z > 350 and boost > 30 and dist_to_ball < 1800:
        return BotDecision.AERIAL
    
    # 6. Attack: If ball is in opponent half and we're close, attack
    if dist_ball_to_opponent_goal < 2000 and dist_to_ball < 900:
        return BotDecision.ATTACK
    
    # 7. Dribble: If ball is on roof or close and slow, dribble
    if abs(car_to_ball.z) < 120 and dist_to_ball < 350 and ball_velocity.length() < 600:
        return BotDecision.DRIBBLE
    
    return BotDecision.NONE
