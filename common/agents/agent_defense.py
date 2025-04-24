import heapq
import random
from common.base_agent import BaseAgent
from common.move import Move

SCIPERS = ["399767", "399484"]

class Agent(BaseAgent):
    def get_move(self):
        # Position actuelle et direction
        x, y = self.all_trains[self.nickname]['position']
        delta_x, delta_y = self.all_trains[self.nickname]['direction']
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
            if 'wagons' in train_data:
                positions_to_avoid.extend(train_data['wagons'])
            
        # Prédire les prochaines positions des autres trains
        for train_name, train_data in self.all_trains.items():
            if train_name != self.nickname and train_data.get('alive', True):
                train_pos = train_data['position']
                train_dir = train_data['direction']
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

        # Si aucun mouvement valide n'est disponible
        if not valid_moves:
            # Continuer tout droit (dans la direction actuelle) même si cela mène à une collision
            if current_direction:
                return current_direction
            # Si pour une raison quelconque, nous n'avons pas de direction actuelle,
            # choisir n'importe quel mouvement sauf le demi-tour
            possible_moves = [move for move in Move if move != opposite_direction]
            return random.choice(possible_moves)

        # === Ajout du mode défensif ===
        # Trouver l'autre train et comparer les nombres de wagons
        other_train = None
        my_wagons_count = len(self.all_trains[self.nickname]['wagons'])
        
        for train_name, train_data in self.all_trains.items():
            if train_name != self.nickname and train_data.get('alive', True):
                other_train = train_data
                break
        
        # Activation du mode défensif si on a suffisamment d'avantage
        defensive_mode = False
        if other_train:
            other_wagons_count = len(other_train.get('wagons', []))
            # Si on a 3+ wagons de plus que l'adversaire, activer le mode défensif
            if my_wagons_count - other_wagons_count >= 3:
                defensive_mode = True
        
        # === Ajout A* vers le passager le plus proche ou la zone de défense ===
        if valid_moves and self.passengers:
            start = (x, y)
            closest_passenger = min(
                self.passengers,
                key=lambda p: abs(p["position"][0] - x) + abs(p["position"][1] - y)
            ) if self.passengers else None
            
            # Trouver la zone de livraison
            if hasattr(self, 'delivery_zone'):
                closest_zone = self.delivery_zone
            else:
                # Fallback si aucune zone de livraison n'est définie
                closest_zone = {"position": (grid_width // 2, grid_height // 2)}
            
            # Stratégie de mouvement basée sur le mode
            delivery_mode = False
            defensive_patrol = False
            
            # En mode défensif, si on a moins de 9 wagons, continuer à collecter
            # sinon, patrouiller autour de la zone de livraison
            if defensive_mode:
                if my_wagons_count >= 9:
                    defensive_patrol = True
                else:
                    # On continue à collecter des passagers pour atteindre 9 wagons
                    if closest_passenger:
                        goal = closest_passenger["position"]
                    else:
                        # S'il n'y a plus de passagers, rester près de la zone de livraison
                        goal = closest_zone['position']
                        defensive_patrol = True
            else:
                # Logique originale
                dist_to_zone = abs(closest_zone['position'][0] - x) + abs(closest_zone['position'][1] - y)
                if closest_passenger:
                    dist_to_passenger = abs(closest_passenger['position'][0] - x) + abs(closest_passenger['position'][1] - y)
                    
                    # Décider si on doit livrer ou ramasser des passagers
                    if my_wagons_count >= 1 and dist_to_zone < dist_to_passenger:
                        delivery_mode = True
                    if my_wagons_count >= 5 and dist_to_zone > dist_to_passenger:
                        delivery_mode = False
                    if my_wagons_count >= 5 and dist_to_zone < dist_to_passenger:
                        delivery_mode = True
                    if my_wagons_count >= 6:
                        delivery_mode = True
                        
                    if delivery_mode:
                        goal = closest_zone['position']
                    else:
                        goal = closest_passenger["position"]
                else:
                    # S'il n'y a plus de passagers, se diriger vers la zone de livraison
                    goal = closest_zone['position']
                    
                # Réinitialiser le mode livraison si on n'a pas de wagons
                if my_wagons_count == 0:
                    delivery_mode = False
                    if closest_passenger:
                        goal = closest_passenger["position"]
                    else:
                        # S'il n'y a plus de passagers, se diriger vers la zone de livraison
                        goal = closest_zone['position']
            
            # Mode de patrouille défensive autour de la zone de livraison
            if defensive_patrol:
                # Obtenir les données de la zone de livraison
                zone_x, zone_y = closest_zone['position']
                zone_width = closest_zone.get('width', cell_size)  # Largeur de 40 pixels
                zone_height = closest_zone.get('height', cell_size)  # Hauteur de 20 pixels
                
                # Créer un chemin de patrouille autour de la zone de livraison
                # en tenant compte de ses dimensions réelles
                patrol_positions = [
                    # Coin supérieur gauche et bord supérieur
                    (zone_x - cell_size, zone_y - cell_size),
                    (zone_x, zone_y - cell_size),
                    (zone_x + zone_width // 2, zone_y - cell_size),
                    (zone_x + zone_width, zone_y - cell_size),
                    
                    # Bord droit
                    (zone_x + zone_width, zone_y),
                    (zone_x + zone_width, zone_y + zone_height // 2),
                    (zone_x + zone_width, zone_y + zone_height),
                    
                    # Bord inférieur
                    (zone_x + zone_width // 2, zone_y + zone_height),
                    (zone_x, zone_y + zone_height),
                    
                    # Bord gauche
                    (zone_x - cell_size, zone_y + zone_height // 2),
                    (zone_x - cell_size, zone_y)
                ]
                
                # Trouver le point de patrouille le plus proche qui n'est pas notre position actuelle
                valid_patrol_positions = [pos for pos in patrol_positions if 
                                        0 <= pos[0] < grid_width and 
                                        0 <= pos[1] < grid_height and
                                        pos != (x, y)]
                
                if valid_patrol_positions:
                    # Utiliser la distance de Manhattan pour trouver le point le plus proche
                    closest_patrol_point = min(valid_patrol_positions, 
                                            key=lambda p: abs(p[0] - x) + abs(p[1] - y))
                    goal = closest_patrol_point
                else:
                    # Si aucun point de patrouille n'est valide, aller vers un point juste devant la zone
                    backup_points = [
                        (zone_x - cell_size, zone_y),              # Gauche
                        (zone_x, zone_y - cell_size),              # Haut
                        (zone_x + zone_width, zone_y),             # Droite
                        (zone_x, zone_y + zone_height)             # Bas
                    ]
                    valid_backups = [pos for pos in backup_points if 
                                    0 <= pos[0] < grid_width and 
                                    0 <= pos[1] < grid_height]
                    
                    if valid_backups:
                        goal = min(valid_backups, key=lambda p: abs(p[0] - x) + abs(p[1] - y))
                    else:
                        # En dernier recours, se diriger vers le centre de la zone
                        goal = (zone_x + zone_width // 2, zone_y + zone_height // 2)
            
            # Utiliser A* pour trouver le chemin vers l'objectif
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