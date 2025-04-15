import heapq
import random
from common.base_agent import BaseAgent
from common.move import Move

SCIPERS = ["399767", "399484"]

class Agent(BaseAgent):
    visited_delivery_positions = set()
    delivery_mode = False
    initialized = False
    max_wagons = 3

    def get_move(self):
        # Initialisation unique
        if not self.initialized:
            self.visited_delivery_positions = set()
            self.delivery_mode = False
            self.initialized = True

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

        # Positions à éviter
        positions_to_avoid = []
        for train_data in self.all_trains.values():
            positions_to_avoid.extend(train_data.get('wagons', []))
            positions_to_avoid.append(train_data['position'])
        for train_name, train_data in self.all_trains.items():
            if train_name != self.nickname and train_data.get('alive', True):
                train_pos = train_data['position']
                train_dir = train_data['direction']
                next_pos = (
                    train_pos[0] + train_dir[0] * cell_size,
                    train_pos[1] + train_dir[1] * cell_size
                )
                positions_to_avoid.append(next_pos)

        # Mouvements valides
        valid_moves = []
        for move, delta in move_deltas.items():
            nx, ny = x + delta[0], y + delta[1]
            if 0 <= nx < grid_width and 0 <= ny < grid_height and (nx, ny) not in positions_to_avoid:
                valid_moves.append(move)

        # Éviter demi-tour
        current_direction = None
        opposite_direction = None
        for move, delta in move_deltas.items():
            if delta == (delta_x * cell_size, delta_y * cell_size):
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
            if current_direction:
                return current_direction
            possible_moves = [move for move in Move if move != opposite_direction]
            return random.choice(possible_moves)

        # Récupérer le nombre de wagons actuel
        current_wagons = len(self.all_trains[self.nickname].get('wagons', []))
        
        # Activer le mode livraison si assez de wagons
        if current_wagons >= self.max_wagons:
            self.delivery_mode = True

        # Vérifier si on est dans une zone de livraison
        in_delivery_zone = False
        zone_in = None
        if hasattr(self, '') and self.delivery_zone:  # CORRECTION:  (pluriel)
            for zone in self.delivery_zone:
                zx, zy = zone["position"]
                zw, zh = zone["width"], zone["height"]
                if zx <= x < zx + zw and zy <= y < zy + zh:
                    in_delivery_zone = True
                    zone_in = zone
                    self.visited_delivery_positions.add((x, y))
                    break

        # Si en livraison et dans la zone, larguer des wagons et visiter plusieurs cases
        if self.delivery_mode:
            if in_delivery_zone and zone_in is not None:
                # NOUVEAU: Lorsque dans la zone, larguer un wagon si possible
                if current_wagons > 0 and hasattr(self, 'drop_wagon'):
                    self.drop_wagon()
                
                # Si on a visité assez de positions dans la zone, désactiver mode livraison
                if len(self.visited_delivery_positions) >= 2:
                    self.delivery_mode = False
                    self.visited_delivery_positions = set()
                # Sinon explorer la zone pour visiter d'autres cases
                else:
                    # Chercher à visiter une nouvelle case dans la zone
                    zx, zy = zone_in["position"]
                    zw, zh = zone_in["width"], zone_in["height"]
                    unvisited_moves = []
                    
                    for move, (dx, dy) in move_deltas.items():
                        nx, ny = x + dx, y + dy
                        new_pos = (nx, ny)
                        # Vérifier que la position est dans la zone de livraison
                        if (zx <= nx < zx + zw and zy <= ny < zy + zh and
                            new_pos not in self.visited_delivery_positions and
                            move in valid_moves):
                            unvisited_moves.append(move)
                    
                    if unvisited_moves:
                        return random.choice(unvisited_moves)
            
            # Si on n'est pas dans une zone de livraison mais en mode livraison
            else:
                # Aller au centre de la zone la plus proche
                min_dist = float('inf')
                target = None
                
                for zone in self.delivery_zone:  # CORRECTION:  (pluriel)
                    print("zone:", zone, type(zone))
                    zx, zy = zone["position"]
                    zw, zh = zone["width"], zone["height"]
                    cx, cy = zx + zw // 2, zy + zh // 2
                    dist = abs(cx - x) + abs(cy - y)
                    if dist < min_dist:
                        min_dist = dist
                        target = (cx, cy)
                
                if target:
                    path = self.a_star((x, y), target, grid_width, grid_height, cell_size)
                    if path and len(path) > 1:
                        nx, ny = path[1]
                        for move, (dx, dy) in move_deltas.items():
                            if (x + dx, y + dy) == (nx, ny) and move in valid_moves:
                                return move

        # Si pas en livraison ou livraison terminée, chercher un passager
        if valid_moves and hasattr(self, 'passengers') and self.passengers:
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

        return []  # Aucun chemin