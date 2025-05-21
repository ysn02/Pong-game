import gym
from gym import spaces
import numpy as np
import random


class CustomPongEnv(gym.Env):
    def __init__(self):
        super(CustomPongEnv, self).__init__()

        # Action space: 0 = up, 1 = down, 2 = stay
        self.action_space = spaces.Discrete(3)

        # Observation space: [ball_x, ball_y, paddle_y, score_diff]
        self.observation_space = spaces.Box(low=-1, high=1, shape=(4,), dtype=np.float32)

        self.reset()

    def reset(self):
        self.ball_x = 0.5
        self.ball_y = 0.5
        self.paddle_y = 0.5
        self.ball_speed_x = -0.02  # ball moving towards paddle
        self.ball_speed_y = np.random.uniform(-0.01, 0.01)
        self.player_score = 0
        self.ai_score = 0
        return self._get_obs()

    def _get_obs(self):
        score_diff = np.clip((self.player_score - self.ai_score) / 10.0, -1, 1)
        return np.array([self.ball_x, self.ball_y, self.paddle_y, score_diff], dtype=np.float32)

    def step(self, action):
        # Move paddle smoothly
        move_amount = 0.02  # smaller value for smoothness

        if action == 0:
            self.paddle_y -= move_amount
        elif action == 1:
            self.paddle_y += move_amount
        
        self.paddle_y = np.clip(self.paddle_y, 0, 1)

        # Move ball
        self.ball_x += self.ball_speed_x
        self.ball_y += self.ball_speed_y

        # Bounce off top/bottom
        if self.ball_y <= 0 or self.ball_y >= 1:
            self.ball_speed_y *= -1

        reward = 0
        done = False

        # Ball reaches paddle (left side)
        if self.ball_x <= 0:
            if abs(self.ball_y - self.paddle_y) < 0.15:
                reward = 1  # Good hit
                self.player_score += 1
                self.reset_ball()
            else:
                reward = -1  # Missed
                self.ai_score += 1
                self.reset_ball()

        # Ball goes too far right (shouldn't happen)
        if self.ball_x > 1.2:
            done = True

        obs = self._get_obs()
        return obs, reward, done, {}

    def reset_ball(self):
        self.ball_x = 0.5
        self.ball_y = 0.5
        self.ball_speed_x = -0.02
        self.ball_speed_y = np.random.uniform(-0.01, 0.01)

    def render(self, mode='human'):
        pass  # Optional: we don't need visualization for training

    def close(self):
        pass

# --- Smooth and adaptive trained AI move ---

import random

def trained_ai_move(ball, paddle2, model, player_score, ai_score, WIDTH, HEIGHT):

    ball_x_normalized = ball.x / WIDTH
    ball_y_normalized = ball.y / HEIGHT
    paddle_y_normalized = paddle2.y / HEIGHT

    score_diff = np.clip((player_score - ai_score) / 10.0, -1, 1)

    obs = np.array([ball_x_normalized, ball_y_normalized, paddle_y_normalized, score_diff], dtype=np.float32)
    obs = obs.reshape(1, -1)

    # Predict action
    action, _states = model.predict(obs, deterministic=True)

    # Smooth movement based on prediction
    move_speed = 3

    # Adjust AI difficulty dynamically
    if player_score < ai_score:
        move_speed *= 0.6  # Easier
    elif player_score == ai_score:
        move_speed *= 1.0  # Medium
    else:
        move_speed *= 1.4  # Harder

    # --- Add realistic miss behavior ---
    miss_chance = 0

    # If ball is near AI side, increase chance to miss
    if ball.x > WIDTH * 0.7:
        miss_chance = 0.1  # 10% chance to react badly

    # If AI is winning by a lot, it becomes a bit sloppy
    if ai_score - player_score > 3:
        miss_chance += 0.1  # Extra 10%

    if random.random() < miss_chance:
        # Intentionally make a wrong move or slow down
        if action == 0:
            action = 2  # stay instead of moving up
        elif action == 1:
            action = 2  # stay instead of moving down

    # --- Move paddle based on (possibly modified) action ---
    if action == 0:
        paddle2.y -= move_speed
    elif action == 1:
        paddle2.y += move_speed
    # action == 2 means stay

    # Clamp paddle inside the screen (in pixels)
    paddle2.y = max(0, min(HEIGHT - paddle2.height, paddle2.y))

    return action

# Example ball and paddle classes
class Ball:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class Paddle:
    def __init__(self, y):
        self.y = y
