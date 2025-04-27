import heapq
import random
from common.base_agent import BaseAgent
from common.move import Move

SCIPERS = ["399767", "399484"]

class Agent(BaseAgent):
    def get_move(self):
        # Position actuelle et direction
        x, y = self.all_trains[self.nickname]["position"]
        delta_x, delta_y = self.all_trains[self.nickname]["direction"]
        grid_width = self.game_width
        grid_height = self.game_height
        cell_size = self.cell_size

        # Définition des déplacements
        move_deltas = {
            Move.UP: (0, -cell_size),
            Move.DOWN: (0, cell_size),
            Move.LEFT: (-cell_size, 0),
            Move.RIGHT: (cell_size, 0),
        }

        # Collecte de toutes les positions des wagons pour éviter les collisions
        positions_to_avoid = []
        for train_name, train_data in self.all_trains.items():
            # Ajouter les positions des wagons de tous les trains
            if "wagons" in train_data:
                positions_to_avoid.extend(train_data["wagons"])
            
        # Prédire les prochaines positions des autres trains
        for train_name, train_data in self.all_trains.items():
            if train_name != self.nickname and train_data.get("alive", True):
                train_pos = train_data["position"]
                train_dir = train_data["direction"]
                # Calculer la prochaine position prévue de ce train
                next_pos = (
                    train_pos[0] + train_dir[0] * cell_size,
                    train_pos[1] + train_dir[1] * cell_size
                )
                positions_to_avoid.append(next_pos)
                # Ajouter aussi la position actuelle du train
                positions_to_avoid.append(train_pos)

        # Vérifier les mouvements valides (éviter les murs)
        valid_moves = []
        for move, delta in move_deltas.items():
            new_x = x + delta[0]
            new_y = y + delta[1]
            new_pos = (new_x, new_y)
            if 0 <= new_x < grid_width and 0 <= new_y < grid_height and new_pos not in positions_to_avoid:
                # Vérifier si la nouvelle position ne contient pas de wagon
                valid_moves.append(move)

        # Éviter de faire demi-tour
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
            # Retirer le mouvement opposé des mouvements valides
            if opposite_direction in valid_moves:
                valid_moves.remove(opposite_direction)

        # Si aucun mouvement valide n"est disponible
        if not valid_moves:
            # Continuer tout droit (dans la direction actuelle) même si cela mène à une collision
            if current_direction:
                return current_direction
            # Si pour une raison quelconque, nous n"avons pas de direction actuelle,
            # choisir n"importe quel mouvement sauf le demi-tour
            possible_moves = [move for move in Move if move != opposite_direction]
            return random.choice(possible_moves)

        # === Ajout A* vers le passager le plus proche ===
        if valid_moves and self.passengers:
            start = (x, y)
            closest_passenger = min(
                self.passengers,
                key=lambda p: abs(p["position"][0] - x) + abs(p["position"][1] - y)
            )
            goal = closest_passenger["position"]
            path = self.a_star(start, goal, grid_width, grid_height, cell_size)

            if path and len(path) > 1:
                next_step = path[1]
                dx = next_step[0] - x
                dy = next_step[1] - y
                for move, (mdx, mdy) in move_deltas.items():
                    if (dx, dy) == (mdx, mdy) and move in valid_moves:
                        return move

        # Fallback : mouvement valide aléatoire
        if not valid_moves:
            return random.choice(list(Move))

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