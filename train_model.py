# train_model.py

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from custom_pong_env import CustomPongEnv

def train_and_save_model():
    # Create the environment
    env = DummyVecEnv([lambda: CustomPongEnv()])  # Wrap environment for compatibility

    # Create the PPO model
    model = PPO(
        policy='MlpPolicy',
        env=env,
        verbose=1,
        learning_rate=2.5e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99
    )

    # Train the model
    print("Training the model...")
    model.learn(total_timesteps=200_000)  # Increase timesteps for better training

    # Save the model
    model.save("trained_model")
    print("Model saved as 'trained_model.zip'!")

    # Close the environment
    env.close()

if __name__ == "__main__":
    train_and_save_model()
