from pydantic import BaseModel

from common.agent_config import AgentConfig


class ServerConfig(BaseModel):
    # Host should either be 127.0.0.1 if you only want to accept local connections
    # or 0.0.0.0 if you want to accept local and remote connections.
    host: str = "0.0.0.0"

    # Port on which to listen.
    port: int = 5555

    # Numbers of trains in each room.
    nb_clients_per_room: int = 2

    # If True, allows multiple connections from the same IP address.
    allow_multiple_connections: bool = True

    # When a train hits another train or the game edge, it dies. This controls
    # how much time the user must wait before they can respawn a new train.
    respawn_cooldown_seconds: float = 5.0

    # How long to wait before considering a client as disconnected.
    client_timeout_seconds: float = 2.0

    # Controls the game speed (in frames per second). A lower speed could be
    # useful for debugging purpose.
    tick_rate: int = 60

    # Duration of each game.
    game_duration_seconds: int = 300  # 300 seconds == 5 minutes

    # Amount of time clients will waiting for other clients to join before the
    # game is started with bots replacing any missing clients.
    waiting_time_before_bots_seconds: int = 30

    # Maximum number of passengers on a given square.
    max_passengers: int = 3

    # Controls how quickly passenger delivery happens. Depending on this value,
    # the size of the delivery zone, and the number of passengers, a train might
    # have to circle around to complete delivery of all their passengers.
    delivery_cooldown_seconds: float = 0.1

    # Path to an agent file. Change this path to point to one of your agents
    # to use when creating bots (when game_mode is "manual" or "agent" and a client
    # disconnects).
    ai_agent_file_name: str = "ai_agent.py"

    # Local agents configuration, add or remove agents you want to evaluate as needed
    agents: list[AgentConfig] = []

