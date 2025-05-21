import pygame
import sys
import socket
import asyncio
from stable_baselines3 import PPO
import numpy as np

try:
    model = PPO.load("trained_model")
except FileNotFoundError:
    print("Warning: 'trained_model' not found. AI vs Trained AI mode will be unavailable.")
    model = None

WIDTH, HEIGHT = 1000, 600
FPS = 60
SERVER_IP = "127.0.0.1"
PORT = 5555

pygame.init()
CANVAS = pygame.Surface((WIDTH, HEIGHT))
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pong Game")
FONT = pygame.font.Font("Roboto-Regular.ttf", 36)
BIG_FONT = pygame.font.Font("Roboto-Regular.ttf", 60)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLACK = (0, 0, 0)
PADDLE_WIDTH, PADDLE_HEIGHT = 10, 100
BALL_RADIUS = 10
try:
    hit_sound = pygame.mixer.Sound("ping.wav")
except pygame.error:
    print("Error loading sound file")
    hit_sound = None

try:
    menu_bg = pygame.image.load("menu_background.jpg")
    menu_bg = pygame.transform.scale(menu_bg, (WIDTH, HEIGHT))
except pygame.error:
    print("Error loading menu background. Make sure 'menu_background.png' exists.")
    menu_bg = pygame.Surface((WIDTH, HEIGHT))
    menu_bg.fill(BLACK)

class Paddle:
    def __init__(self, x):
        self.rect = pygame.Rect(x, HEIGHT // 2 - PADDLE_HEIGHT // 2, PADDLE_WIDTH, PADDLE_HEIGHT)
        self.speed = 6

    def move(self, up=True):
        if up:
            self.rect.y -= self.speed
        else:
            self.rect.y += self.speed
        self.rect.y = max(0, min(self.rect.y, HEIGHT - PADDLE_HEIGHT))

    def draw(self):
        pygame.draw.rect(CANVAS, WHITE, self.rect)

class Ball:
    def __init__(self, x, y, vx=5, vy=3):
        self.x = x
        self.y = y
        self.radius = 10
        self.vx = vx
        self.vy = vy
        self.speed_multiplier = 1.0
        self.time_since_speed_increase = 0

    def update(self):
        self.x += self.vx * self.speed_multiplier
        self.y += self.vy * self.speed_multiplier

        if self.y <= 0 or self.y >= HEIGHT - self.radius:
            self.vy *= -1

        self.time_since_speed_increase += 1  # Increment every frame
        if self.time_since_speed_increase >= 300:  # Increase speed every 5 seconds (300 frames at 60 FPS)
            self.speed_multiplier += 0.1
            self.time_since_speed_increase = 0

    def draw(self):
        pygame.draw.circle(CANVAS, WHITE, (int(self.x), int(self.y)), self.radius)

class NetworkedGame:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None
        self.player_id = None
        self.paddle1 = Paddle(20)
        self.paddle2 = Paddle(WIDTH - PADDLE_WIDTH - 20)
        self.ball = Ball(WIDTH // 2, HEIGHT // 2)
        self.score1 = 0
        self.score2 = 0
        self.connected = False
        self.game_over = False

    async def connect(self):
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            print(f"Client: Connected to server at {self.host}:{self.port}")
            data = await self.reader.read(100)
            if not data:
                print("Client: Server sent no data on connect")
                return False
            self.player_id = int(data.decode().strip())
            print(f"Client: You are Player {self.player_id}")
            self.connected = True
            return True
        except Exception as e:
            print(f"Client: Connection failed: {e}")
            return False

    async def send_data(self, data):
        if not self.connected or self.game_over:
            print("Client: Not connected, cannot send data")
            return
        try:
            self.writer.write(f"{data}\n".encode())
            await self.writer.drain()
        except Exception as e:
            print(f"Client: Error sending data: {e}")
            self.connected = False

    async def receive_data(self):
        if not self.connected or self.game_over:
            print("Client: Not connected, cannot receive data")
            return None
        try:
            data = await self.reader.readline()
            if not data:
                print("Client: Server disconnected")
                self.connected = False
                return None
            return data.decode().strip()
        except Exception as e:
            print(f"Client: Error receiving data: {e}")
            self.connected = False
            return None

    async def game_loop(self):
        clock = pygame.time.Clock()
        run = True
        while run and self.connected:
            clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    run = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    action = pause_menu()
                    if action == "menu":
                        return "menu"
                    elif action == "resume":
                        continue

            keys = pygame.key.get_pressed()
            if self.player_id == 1:
                if keys[pygame.K_w]:
                    self.paddle1.move(up=True)
                if keys[pygame.K_s]:
                    self.paddle1.move(up=False)
                send_data = f"PADDLE1_Y:{self.paddle1.rect.y}"
                await self.send_data(send_data)
            elif self.player_id == 2:
                if keys[pygame.K_UP]:
                    self.paddle2.move(up=True)
                if keys[pygame.K_DOWN]:
                    self.paddle2.move(up=False)
                send_data = f"PADDLE2_Y:{self.paddle2.rect.y}"
                await self.send_data(send_data)

            received_data = await self.receive_data()
            if received_data:
                parts = received_data.split(":")
                if len(parts) >= 8:
                    try:
                        self.paddle1.rect.y = int(parts[1])
                        self.paddle2.rect.y = int(parts[3])
                        self.ball.x = float(parts[5])
                        self.ball.y = float(parts[7])
                        if len(parts) > 13:
                            self.score1 = int(parts[13])
                            self.score2 = int(parts[15])
                    except ValueError as e:
                        print(f"Client {self.player_id} Error parsing data: {e}, Data: {received_data}")
                elif "GAME_OVER" in received_data:
                    self.game_over = True
                    run = False
                else:
                    print(f"Client {self.player_id}: Received invalid data format: {received_data}")

            if not self.connected:
                run = False

            if not self.game_over:
                if received_data and len(parts) >= 8:
                    try:
                        self.ball.x = float(parts[5])
                        self.ball.y = float(parts[7])
                        self.paddle1.rect.y = int(parts[1])
                        self.paddle2.rect.y = int(parts[3])
                        if len(parts) > 13:
                            self.score1 = int(parts[13])
                            self.score2 = int(parts[15])
                    except ValueError:
                        pass
                draw(self.paddle1, self.paddle2, self.ball, self.score1, self.score2)
                WIN.blit(CANVAS, (0, 0))
                pygame.display.update()
                CANVAS.fill(BLACK)

        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        return "menu"

async def run_networked_game():
    game = NetworkedGame(SERVER_IP, PORT)
    if await game.connect():
        return await game.game_loop()
    else:
        return "connection_error"

def draw_center_line():
    for y in range(0, HEIGHT, 20):
        if y % 40 == 0:
            pygame.draw.line(CANVAS, WHITE, (WIDTH // 2, y), (WIDTH // 2, y + 20), 2)

def draw_score(score1, score2):
    label1 = FONT.render("Player 1", True, WHITE)
    label2 = FONT.render("Player 2", True, WHITE)
    CANVAS.blit(label1, (WIDTH // 4 - label1.get_width() // 2, 20))
    CANVAS.blit(label2, (3 * WIDTH // 4 - label2.get_width() // 2, 20))
    score = FONT.render(f"{score1}   {score2}", True, WHITE)
    CANVAS.blit(score, (WIDTH // 2 - score.get_width() // 2, 60))

def draw(p1, p2, ball, score1, score2):
    draw_center_line()
    p1.draw()
    p2.draw()
    ball.draw()
    draw_score(score1, score2)

def ai_move(ball, ai_paddle, difficulty):
    speed = {"Easy": 3, "Medium": 5, "Hard": 7}[difficulty]
    if ai_paddle.rect.centery < ball.y:
        ai_paddle.rect.y += speed
    elif ai_paddle.rect.centery > ball.y:
        ai_paddle.rect.y -= speed
    ai_paddle.rect.y = max(0, min(ai_paddle.rect.y, HEIGHT - PADDLE_HEIGHT))

def trained_ai_move(ball, paddle2):
    if model is None:
        return
    obs = [ball.x, ball.y, 0, 0]
    obs = np.array(obs).reshape(1, -1)
    action, _states = model.predict(obs, deterministic=True)
    if action == 0:
        paddle2.move(up=True)
    elif action == 1:
        paddle2.move(up=False)
        
def play_vs_trained_ai():
    paddle1 = Paddle(20)
    paddle2 = Paddle(WIDTH - PADDLE_WIDTH - 20)
    ball = Ball(WIDTH // 2, HEIGHT // 2)
    clock = pygame.time.Clock()
    score1 = score2 = 0
    run = True
    while run:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                action = pause_menu()
                if action == "menu":
                    return
                elif action == "resume":
                    continue
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            paddle1.move(up=True)
        if keys[pygame.K_s]:
            paddle1.move(up=False)
        trained_ai_move(ball, paddle2)
        ball.update()
        # Ball collision with paddles
        if paddle1.rect.colliderect(ball.x - BALL_RADIUS, ball.y - BALL_RADIUS, BALL_RADIUS * 2, BALL_RADIUS * 2):
            ball.vx *= -1
            if hit_sound:
                hit_sound.play()
        if paddle2.rect.colliderect(ball.x - BALL_RADIUS, ball.y - BALL_RADIUS, BALL_RADIUS * 2, BALL_RADIUS * 2):
            ball.vx *= -1
            if hit_sound:
                hit_sound.play()
        # Scoring
        if ball.x < 0:
            score2 += 1
            ball.x, ball.y = WIDTH // 2, HEIGHT // 2
            ball.vx *= -1
            ball.vy *= -1
        if ball.x > WIDTH:
            score1 += 1
            ball.x, ball.y = WIDTH // 2, HEIGHT // 2
            ball.vx *= -1
            ball.vy *= -1
        draw(paddle1, paddle2, ball, score1, score2)
        WIN.blit(CANVAS, (0, 0))
        pygame.display.update()
        CANVAS.fill(BLACK)

def pause_menu():
    options = ["R - Resume", "M - Main Menu", "Q - Quit"]
    while True:
        CANVAS.fill(BLACK)
        for i, opt in enumerate(options):
            txt = FONT.render(opt, True, WHITE)
            CANVAS.blit(txt, (WIDTH // 2 - txt.get_width() // 2, 200 + i * 60))
        WIN.blit(CANVAS, (0, 0))
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    return "resume"
                elif event.key == pygame.K_m:
                    return "menu"
                elif event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()

def main_menu():
    options = ["Play Local", "Play vs AI", "Play vs Trained AI", "Online Multiplayer", "Quit"]
    selected = 0
    while True:
        CANVAS.blit(menu_bg, (0, 0))
        title = BIG_FONT.render("PONG GAME", True, WHITE)
        CANVAS.blit(title, (WIDTH // 2 - title.get_width() // 2, 60))
        for i, opt in enumerate(options):
            color = RED if i == selected else WHITE
            txt = FONT.render(opt, True, color)
            CANVAS.blit(txt, (WIDTH // 2 - txt.get_width() // 2, 200 + i * 60))
        WIN.blit(CANVAS, (0, 0))
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(options)
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                elif event.key == pygame.K_RETURN:
                    return options[selected]

def difficulty_menu():
    options = ["Easy", "Medium", "Hard", "Go Back"]
    selected = 0
    while True:
        CANVAS.blit(menu_bg, (0, 0))
        txt = FONT.render("Select Difficulty:", True, WHITE)
        CANVAS.blit(txt, (WIDTH // 2 - txt.get_width() // 2, 100))
        for i, opt in enumerate(options):
            color = RED if i == selected else WHITE
            txt = FONT.render(opt, True, color)
            CANVAS.blit(txt, (WIDTH // 2 - txt.get_width() // 2, 250 + i * 50))
        WIN.blit(CANVAS, (0, 0))
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(options)
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                elif event.key == pygame.K_RETURN:
                    if options[selected] == "Go Back":
                        return None
                    else:
                        return options[selected]

def show_waiting_screen():
    while True:
        CANVAS.blit(menu_bg, (0, 0))
        txt = FONT.render("Waiting for another player to join...", True, WHITE)
        esc_txt = FONT.render("Press ESC to cancel", True, RED)
        CANVAS.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT // 2 - 50))
        CANVAS.blit(esc_txt, (WIDTH // 2 - esc_txt.get_width() // 2, HEIGHT // 2 + 10))
        WIN.blit(CANVAS, (0, 0))
        pygame.display.update()
        CANVAS.fill(BLACK)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return False
        pygame.time.delay(100)

def show_connection_error():
    while True:
        CANVAS.blit(menu_bg, (0, 0))
        txt = FONT.render("Connection Failed!", True, RED)
        esc_txt = FONT.render("Press ESC to return to menu", True, WHITE)
        CANVAS.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT // 2 + 10))
        WIN.blit(CANVAS, (0, 0))
        pygame.display.update()
        CANVAS.fill(BLACK)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return  # Return to the main menu
        pygame.time.delay(100) # Add delay

async def play_online():
    game = NetworkedGame(SERVER_IP, PORT)
    if await game.connect():
        # Show waiting screen here
        if show_waiting_screen() == False:
            return
        result = await game.game_loop()
        if result == "connection_error":
            show_connection_error()
        elif result == "menu":
            return
    else:
        show_connection_error()

def play_local():
    paddle1 = Paddle(20)
    paddle2 = Paddle(WIDTH - PADDLE_WIDTH - 20)
    ball = Ball(WIDTH // 2, HEIGHT // 2)
    clock = pygame.time.Clock()
    score1 = 0
    score2 = 0
    run = True
    while run:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                action = pause_menu()
                if action == "menu":
                    return
                elif action == "resume":
                    continue
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            paddle1.move(up=True)
        if keys[pygame.K_s]:
            paddle1.move(up=False)
        if keys[pygame.K_UP]:
            paddle2.move(up=True)
        if keys[pygame.K_DOWN]:
            paddle2.move(up=False)
        ball.update()
        # Ball collision with paddles
        if paddle1.rect.colliderect(ball.x - BALL_RADIUS, ball.y - BALL_RADIUS, BALL_RADIUS * 2, BALL_RADIUS * 2):
            ball.vx *= -1
            if hit_sound:
                hit_sound.play()
        if paddle2.rect.colliderect(ball.x - BALL_RADIUS, ball.y - BALL_RADIUS, BALL_RADIUS * 2, BALL_RADIUS * 2):
            ball.vx *= -1
            if hit_sound:
                hit_sound.play()
        # Scoring
        if ball.x < 0:
            score2 += 1
            ball.x, ball.y = WIDTH // 2, HEIGHT // 2
            ball.vx *= -1
            ball.vy *= -1
        if ball.x > WIDTH:
            score1 += 1
            ball.x, ball.y = WIDTH // 2, HEIGHT // 2
            ball.vx *= -1
            ball.vy *= -1
        draw(paddle1, paddle2, ball, score1, score2)
        WIN.blit(CANVAS, (0, 0))
        pygame.display.update()
        CANVAS.fill(BLACK)

def play_vs_ai(difficulty="Medium"):
    paddle1 = Paddle(20)
    paddle2 = Paddle(WIDTH - PADDLE_WIDTH - 20)
    ball = Ball(WIDTH // 2, HEIGHT // 2)
    clock = pygame.time.Clock()
    score1 = 0
    score2 = 0
    run = True
    while run:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                action = pause_menu()
                if action == "menu":
                    return
                elif action == "resume":
                    continue
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            paddle1.move(up=True)
        if keys[pygame.K_s]:
            paddle1.move(up=False)
        ai_move(ball, paddle2, difficulty)
        ball.update()
        # Ball collision with paddles
        if paddle1.rect.colliderect(ball.x - BALL_RADIUS, ball.y - BALL_RADIUS, BALL_RADIUS * 2, BALL_RADIUS * 2):
            ball.vx *= -1
            if hit_sound:
                hit_sound.play()
        if paddle2.rect.colliderect(ball.x - BALL_RADIUS, ball.y - BALL_RADIUS, BALL_RADIUS * 2, BALL_RADIUS * 2):
            ball.vx *= -1
            if hit_sound:
                hit_sound.play()
        # Scoring
        if ball.x < 0:
            score2 += 1
            ball.x, ball.y = WIDTH // 2, HEIGHT // 2
            ball.vx *= -1
            ball.vy *= -1
        if ball.x > WIDTH:
            score1 += 1
            ball.x, ball.y = WIDTH // 2, HEIGHT // 2
            ball.vx *= -1
            ball.vy *= -1
        draw(paddle1, paddle2, ball, score1, score2)
        WIN.blit(CANVAS, (0, 0))
        pygame.display.update()
        CANVAS.fill(BLACK)

def main():
    while True:
        choice = main_menu()
        if choice == "Play Local":
            play_local()
        elif choice == "Play vs AI":
            level = difficulty_menu()
            if level:
                play_vs_ai(level)
        elif choice == "Play vs Trained AI":
            play_vs_trained_ai()
        elif choice == "Online Multiplayer":
            asyncio.run(play_online())
        elif choice == "Quit":
            pygame.quit()
            sys.exit()
if __name__ == "__main__":
    main()
