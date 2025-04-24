import heapq
import random
from common.base_agent import BaseAgent
from common.move import Move
from server.high_score import HighScore  # <-- ajouté en haut avec les imports

SCIPERS = ["399767", "399484"]

class Agent(BaseAgent):
    def get_move(self):
        x, y = self.all_trains[self.nickname]['position']
        delta_x, delta_y = self.all_trains[self.nickname]['direction']
        grid_width = self.game_width
        grid_height = self.game_height
        cell_size = self.cell_size

        move_deltas = {
            Move.UP: (0, -cell_size),
            Move.DOWN: (0, cell_size),
            Move.LEFT: (-cell_size, 0),
            Move.RIGHT: (cell_size, 0),
        }

        positions_to_avoid = []
        for train_name, train_data in self.all_trains.items():
            if 'wagons' in train_data:
                positions_to_avoid.extend(train_data['wagons'])

        for train_name, train_data in self.all_trains.items():
            if train_name != self.nickname and train_data.get('alive', True):
                train_pos = train_data['position']
                train_dir = train_data['direction']
                next_pos = (
                    train_pos[0] + train_dir[0] * cell_size,
                    train_pos[1] + train_dir[1] * cell_size
                )
                positions_to_avoid.extend([next_pos, train_pos])

        valid_moves = []
        for move, delta in move_deltas.items():
            new_x = x + delta[0]
            new_y = y + delta[1]
            new_pos = (new_x, new_y)
            if 0 <= new_x < grid_width and 0 <= new_y < grid_height and new_pos not in positions_to_avoid:
                valid_moves.append(move)

        current_direction = None
        opposite_direction = None
        for move, delta in move_deltas.items():
            if delta == (delta_x * self.cell_size, delta_y * self.cell_size):
                current_direction = move
                break

        if current_direction:
            opposite_moves = {
                Move.UP: Move.DOWN,
                Move.DOWN: Move.UP,
                Move.LEFT: Move.RIGHT,
                Move.RIGHT: Move.LEFT,
            }
            opposite_direction = opposite_moves.get(current_direction)
            if opposite_direction in valid_moves:
                valid_moves.remove(opposite_direction)

        if not valid_moves:
            return current_direction or random.choice([m for m in Move if m != opposite_direction])

        # ==== MODIF: Mode défensif basé sur le score ====
        high_scores = HighScore()
        my_score = high_scores.get_from_nickname(self.nickname)
        my_wagons_count = len(self.all_trains[self.nickname]['wagons'])

        other_train = None
        defensive_mode = False

        for train_name, train_data in self.all_trains.items():
            if train_name != self.nickname and train_data.get('alive', True):
                other_train = train_data
                other_score = high_scores.get_from_nickname(train_name)
                if my_score > other_score:
                    defensive_mode = True
                break

        if valid_moves and self.passengers:
            start = (x, y)
            closest_passenger = min(
                self.passengers,
                key=lambda p: abs(p["position"][0] - x) + abs(p["position"][1] - y)
            )

            closest_zone = getattr(self, 'delivery_zone', {"position": (grid_width // 2, grid_height // 2)})

            delivery_mode = False
            defensive_patrol = False

            if defensive_mode:
                if my_wagons_count >= 9:
                    defensive_patrol = True
                else:
                    goal = closest_passenger["position"] if closest_passenger else closest_zone['position']
                    defensive_patrol = not bool(closest_passenger)
            else:
                dist_zone = abs(closest_zone['position'][0] - x) + abs(closest_zone['position'][1] - y)
                dist_pass = abs(closest_passenger['position'][0] - x) + abs(closest_passenger['position'][1] - y)

                if my_wagons_count >= 1 and dist_zone < dist_pass:
                    delivery_mode = True
                if my_wagons_count >= 5 and dist_zone < dist_pass:
                    delivery_mode = True
                if my_wagons_count >= 6:
                    delivery_mode = True

                goal = closest_zone['position'] if delivery_mode else closest_passenger["position"]

            if my_wagons_count == 0 and closest_passenger:
                delivery_mode = False
                goal = closest_passenger["position"]

            # ==== MODIF: Patrouille défensive autour mais pas dedans ====
            if defensive_patrol:
                zone_x, zone_y = closest_zone['position']
                zone_width = closest_zone.get('width', cell_size)
                zone_height = closest_zone.get('height', cell_size)

                patrol_positions = [
                    (zone_x - cell_size, zone_y - cell_size),
                    (zone_x, zone_y - cell_size),
                    (zone_x + zone_width, zone_y - cell_size),
                    (zone_x + zone_width, zone_y),
                    (zone_x + zone_width, zone_y + zone_height),
                    (zone_x, zone_y + zone_height),
                    (zone_x - cell_size, zone_y + zone_height),
                    (zone_x - cell_size, zone_y)
                ]

                valid_patrol_positions = [
                    pos for pos in patrol_positions
                    if 0 <= pos[0] < grid_width and 0 <= pos[1] < grid_height and pos != (x, y)
                ]

                if valid_patrol_positions:
                    goal = min(valid_patrol_positions, key=lambda p: abs(p[0] - x) + abs(p[1] - y))
                else:
                    goal = (zone_x - cell_size, zone_y)

            path = self.a_star(start, goal, grid_width, grid_height, cell_size)
            if path and len(path) > 1:
                next_step = path[1]
                dx = next_step[0] - x
                dy = next_step[1] - y
                for move, (mdx, mdy) in move_deltas.items():
                    if (dx, dy) == (mdx, mdy) and move in valid_moves:
                        return move

        return random.choice(valid_moves)
    
    def a_star(self, start, goal, grid_width, grid_height, cell_size):
        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])  # Manhattan

        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {start: 0}
        f_score = {start: heuristic(start, goal)}

        directions = [
            (0, -cell_size), (0, cell_size),
            (-cell_size, 0), (cell_size, 0)
        ]

        while open_set:
            _, current = heapq.heappop(open_set)

            if current == goal:
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                return path[::-1]

            for dx, dy in directions:
                neighbor = (current[0] + dx, current[1] + dy)
                if not (0 <= neighbor[0] < grid_width and 0 <= neighbor[1] < grid_height):
                    continue

                tentative_g = g_score[current] + 1
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

        return []  # Aucun chemin trouvé