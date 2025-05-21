import asyncio
import socket
import pygame 
import random

async def handle_client(reader, writer, player_id, game_state):
    """Handles communication with a single client."""
    addr = writer.get_extra_info('peername')
    print(f"Server: Connected by {addr} as Player {player_id}")

    try:
        # Send the player ID to the client
        writer.write(f"{player_id}\n".encode())
        await writer.drain()

        async for line in reader:
            try:
                data = line.decode().strip()
                print(f"Server Received from Player {player_id}: {data}")
                if not data:
                    continue

                # Update game state based on client input
                if player_id == 1 and data.startswith("PADDLE1_Y:"):
                    try:
                        game_state["paddle1_y"] = int(data.split(":")[1])
                    except ValueError:
                        pass
                elif player_id == 2 and data.startswith("PADDLE2_Y:"):
                    try:
                        game_state["paddle2_y"] = int(data.split(":")[1])
                    except ValueError:
                        pass

            except Exception as e:
                print(f"Server: Error processing data from Player {player_id}: {e}")
                break

    except ConnectionResetError:
        print(f"Server: Player {player_id} disconnected unexpectedly.")
    finally:
        print(f"Server: Closed connection with Player {player_id}")
        if player_id in game_state["players"]:
            del game_state["players"][player_id]
        writer.close()

async def broadcast_game_state(state, players):
    """Broadcasts the current game state to all connected players."""
    game_data_str = (
        f"PADDLE1_Y:{state.get('paddle1_y', 300)}:"
        f"PADDLE2_Y:{state.get('paddle2_y', 300)}:"
        f"BALL_X:{state.get('ball_x', 500)}:"
        f"BALL_Y:{state.get('ball_y', 300)}:"
        f"BALL_VEL_X:{state.get('ball_vel_x', 5)}:"
        f"BALL_VEL_Y:{state.get('ball_vel_y', 5)}:"
        f"SCORE1:{state.get('score1', 0)}:"
        f"SCORE2:{state.get('score2', 0)}\n"
    )
    game_data = game_data_str.encode()
    print(f"Server Broadcasting: {game_data_str.strip()}")

    for writer in players.values():
        try:
            writer.write(game_data)
            await writer.drain()
        except ConnectionError:
            pass

async def game_logic(game_state):
    """Manages the game logic and updates the game state."""
    width, height = 1000, 600
    ball_radius = 10
    paddle_height = 100
    paddle_width = 10

    while True:
        if len(game_state["players"]) == 2:
            # Get paddle positions
            p1_y = game_state.get("paddle1_y", height // 2 - paddle_height // 2)
            p2_y = game_state.get("paddle2_y", height // 2 - paddle_height // 2)

            # Update ball position
            game_state["ball_x"] += game_state["ball_vel_x"]
            game_state["ball_y"] += game_state["ball_vel_y"]

            # Ball collision with top/bottom walls
            if game_state["ball_y"] <= ball_radius or game_state["ball_y"] >= height - ball_radius:
                game_state["ball_vel_y"] *= -1

            # Ball collision with paddles
            paddle1_rect = pygame.Rect(20, p1_y, paddle_width, paddle_height)
            paddle2_rect = pygame.Rect(width - paddle_width - 20, p2_y, paddle_width, paddle_height)
            ball_rect = pygame.Rect(game_state["ball_x"] - ball_radius, game_state["ball_y"] - ball_radius, ball_radius * 2, ball_radius * 2)

            if ball_rect.colliderect(paddle1_rect) and game_state["ball_vel_x"] < 0:
                game_state["ball_vel_x"] *= -1
                game_state["ball_vel_y"] += random.uniform(-2, 2)
            elif ball_rect.colliderect(paddle2_rect) and game_state["ball_vel_x"] > 0:
                game_state["ball_vel_x"] *= -1
                game_state["ball_vel_y"] += random.uniform(-2, 2)

            # Scoring
            if game_state["ball_x"] < 0:
                game_state["score2"] += 1
                game_state["ball_x"], game_state["ball_y"] = width // 2, height // 2
                game_state["ball_vel_x"] = abs(game_state["ball_vel_x"])
                game_state["ball_vel_y"] = random.uniform(-5, 5)
            elif game_state["ball_x"] > width:
                game_state["score1"] += 1
                game_state["ball_x"], game_state["ball_y"] = width // 2, height // 2
                game_state["ball_vel_x"] = -abs(game_state["ball_vel_x"])
                game_state["ball_vel_y"] = random.uniform(-5, 5)

            # Keep velocities within reasonable bounds
            game_state["ball_vel_x"] = max(-10, min(game_state["ball_vel_x"], 10))
            game_state["ball_vel_y"] = max(-10, min(game_state["ball_vel_y"], 10))

            # Broadcast game state
            await broadcast_game_state(game_state, game_state["players"])
        else:
            await asyncio.sleep(0.1)  # reduced cpu usage

async def serve_client(reader, writer):
    """Handles a new client connection."""
    global next_player_id
    player_id = next_player_id
    game_state["players"][player_id] = writer
    next_player_id += 1
    asyncio.create_task(handle_client(reader, writer, player_id, game_state))

async def main():
    global game_state, next_player_id
    game_state = {
        "paddle1_y": 300,
        "paddle2_y": 300,
        "ball_x": 500,
        "ball_y": 300,
        "ball_vel_x": 5,
        "ball_vel_y": 5,
        "score1": 0,
        "score2": 0,
        "players": {}
    }
    next_player_id = 1

    server = await asyncio.start_server(
        serve_client, 'localhost', 5555
    )
    addr = server.sockets[0].getsockname()
    print(f'Server: Serving on {addr}')

    # Start the game logic task
    asyncio.create_task(game_logic(game_state))

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    pygame.init()
    asyncio.run(main())