
# 🕹️ Pong Game (Python + Pygame + Trained AI)

A feature-rich Pong game built with **Python** and **Pygame**, featuring:
- Local multiplayer
- Classic AI opponents with difficulty levels
- A trained AI opponent powered by deep reinforcement learning (Stable-Baselines3)
- Menu navigation
- Optional online multiplayer (basic socket connection ready)
- Visual polish including background, fonts, and score display

---

## 🎮 Features

### ✅ Game Modes
- **Play Local**: 2 players on the same keyboard
- **Play vs AI**: Choose between `Easy`, `Medium`, and `Hard`
- **Play vs Trained AI**: A dynamic AI opponent trained using PPO with Stable-Baselines3
- **Online Multiplayer**: Basic socket setup for 1v1 play over LAN/local IP

### 🧠 Trained AI
- Built using a custom OpenAI Gym environment
- Observes ball and paddle positions and score difference
- Adapts its difficulty during gameplay:
  - Plays easier if it’s winning
  - Plays harder if it's losing
- Model trained using PPO (`trained_model.zip`) via `Stable-Baselines3`

---

## 📦 How to Run the Game

### 1. Clone the Repository
You can clone the full project from:

📎 **[https://github.com/MDPONG/pong-game](https://github.com/MDPONG/pong-game)**

```bash
git clone https://github.com/MDPONG/pong-game
cd pong-game
```

### 2. Install Dependencies
Install the required libraries using pip:

```bash
pip install pygame stable-baselines3[extra] gym numpy
```

### 3. Run the Game
In your terminal or command prompt:

```bash
python pong_client.py
```

### 4. (Optional) Train the AI
To retrain the AI model using your custom Gym environment:

```bash
python train_model.py
```

This will generate a new `trained_model.zip`.

---

## 🎮 Controls

**Player 1:**
- `W` – Move Up
- `S` – Move Down

**Player 2:**
- `Arrow Up` – Move Up
- `Arrow Down` – Move Down

**In-Game:**
- `ESC` – Resume or return to menu or quit

---

## 🌐 Online Multiplayer (Optional)

To try the online mode:

1. Start the server:
   ```bash
   python pong_server.py
   ```

2. On both clients:
   ```bash
   python pong_client.py
   ```

3. Select "Online Multiplayer"


---

## 📁 Files Required

Make sure the following files are present:
- `pong_client.py`
- `custom_pong_env.py`
- `train_model.py`
- `pong_server.py`
- `trained_model.zip`
- `ping.wav`
- `menu_background.png`
- `Roboto-Regular.ttf`

---

## 📜 License

This project is provided for educational and non-commercial use only.

---

## 👨‍💻 Author

Developed by Yassine Arbaoui
