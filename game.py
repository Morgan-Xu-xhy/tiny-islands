from typing import List, Dict, Tuple, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import json
import copy
from datetime import datetime
import random
from collections import Counter


class TileType(Enum):
    HOUSES = "houses"
    WAVES = "waves"
    SHIPS = "ships"
    FOREST = "forest"
    MOUNTAIN = "mountain"
    CHURCHES = "churches"
    BEACH = "beach"


class ChunkType(Enum):
    CLUSTER = "cluster"
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


@dataclass
class Choice:
    """Represents a choice available to the player"""
    tile_type: str
    chunk_type: str
    chunk_position: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tileType": self.tile_type,
            "chunkType": self.chunk_type,
            "chunkPosition": self.chunk_position
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Choice':
        return cls(
            tile_type=data["tileType"],
            chunk_type=data["chunkType"],
            chunk_position=data["chunkPosition"]
        )


@dataclass
class PlacedTile:
    """Represents a tile that has been placed on the board"""
    choice: Choice
    tile_position: Tuple[int, int]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chosenChoice": self.choice.to_dict(),
            "tilePosition": self.tile_position
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlacedTile':
        return cls(
            choice=Choice.from_dict(data["chosenChoice"]),
            tile_position=tuple(data["tilePosition"])
        )


@dataclass
class BorderLine:
    """Represents a border line drawn by the player"""
    start_pos: Tuple[int, int]
    end_pos: Tuple[int, int]
    is_horizontal: bool  # True for horizontal line, False for vertical
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "startPos": self.start_pos,
            "endPos": self.end_pos,
            "isHorizontal": self.is_horizontal
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BorderLine':
        return cls(
            start_pos=tuple(data["startPos"]),
            end_pos=tuple(data["endPos"]),
            is_horizontal=data["isHorizontal"]
        )


@dataclass
class Island:
    """Represents an island defined by border lines"""
    border_lines: List[BorderLine]
    enclosed_positions: Set[Tuple[int, int]]
    is_lake: bool  # True if this is a lake (enclosed area within an island)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "borderLines": [line.to_dict() for line in self.border_lines],
            "enclosedPositions": list(self.enclosed_positions),
            "isLake": self.is_lake
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Island':
        return cls(
            border_lines=[BorderLine.from_dict(line) for line in data["borderLines"]],
            enclosed_positions=set(tuple(pos) for pos in data["enclosedPositions"]),
            is_lake=data["isLake"]
        )


@dataclass
class TurnHistory:
    """Represents a single turn's history"""
    chosen_tile: PlacedTile
    discarded_tile: PlacedTile
    border_lines: List[BorderLine]  # Lines drawn during border phase
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chosenChoice": self.chosen_tile.to_dict(),
            "discardedChoice": self.discarded_tile.to_dict(),
            "borderLines": [line.to_dict() for line in self.border_lines]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TurnHistory':
        return cls(
            chosen_tile=PlacedTile.from_dict(data["chosenChoice"]),
            discarded_tile=PlacedTile.from_dict(data["discardedChoice"]),
            border_lines=[BorderLine.from_dict(line) for line in data.get("borderLines", [])]
        )


# === GAME CONSTANTS ===
MAX_BORDER_LINES = 24
GRID_SIZE = 9

# Explicit turn order: 9 choices, then a border draw, repeated 3 times
TURN_ACTIONS = [
    'choice', 'choice', 'choice', 'choice', 'choice', 'choice', 'choice', 'choice', 'choice', 'border',
    'choice', 'choice', 'choice', 'choice', 'choice', 'choice', 'choice', 'choice', 'choice', 'border',
    'choice', 'choice', 'choice', 'choice', 'choice', 'choice', 'choice', 'choice', 'border'
]

@dataclass
class SaveState:
    """Represents all data needed to recreate the exact state of the game"""
    current_turn: int
    choice_history: List[TurnHistory]
    game_id: str
    created_at: str
    placed_tiles: List[PlacedTile]  # All tiles currently on the board
    border_lines: List[BorderLine]  # All border lines drawn so far
    islands: List[Island]  # All islands/lakes formed by border lines
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "currentTurn": self.current_turn,
            "choiceHistory": [turn.to_dict() for turn in self.choice_history],
            "gameId": self.game_id,
            "createdAt": self.created_at,
            "placedTiles": [tile.to_dict() for tile in self.placed_tiles],
            "borderLines": [line.to_dict() for line in self.border_lines],
            "islands": [island.to_dict() for island in self.islands]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SaveState':
        return cls(
            current_turn=data["currentTurn"],
            choice_history=[TurnHistory.from_dict(turn) for turn in data["choiceHistory"]],
            game_id=data["gameId"],
            created_at=data["createdAt"],
            placed_tiles=[PlacedTile.from_dict(tile) for tile in data.get("placedTiles", [])],
            border_lines=[BorderLine.from_dict(line) for line in data.get("borderLines", [])],
            islands=[Island.from_dict(island) for island in data.get("islands", [])]
        )
    
    def save_to_file(self, filename: str) -> None:
        """Save the save state to a JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_file(cls, filename: str) -> 'SaveState':
        """Load a save state from a JSON file"""
        with open(filename, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)


class GameRunner:
    """Controller that runs the game, decides what actions are available and if the game has ended"""
    
    def __init__(self):
        self.grid_size = GRID_SIZE
        self.max_border_lines = MAX_BORDER_LINES
        self.generated_tile_types_debug = []  # For debugging: track all generated tile types
        self.tile_type_list_printed = False   # Ensure print only once
        self.tile_type_pool = []  # Pool for bounded random tile types
        self.tile_type_pool_index = 0  # Track position in pool
    
    def create_new_game(self) -> SaveState:
        """Create a new game save state and generate a new tile type pool"""
        self.tile_type_pool = self.generate_bounded_tile_pool()
        self.tile_type_pool_index = 0
        self.generated_tile_types_debug = []
        self.tile_type_list_printed = False
        return SaveState(
            current_turn=1,
            choice_history=[],
            game_id=f"game_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            created_at=datetime.now().isoformat(),
            placed_tiles=[],
            border_lines=[],
            islands=[]
        )
    
    def decide_action(self, save_state: SaveState) -> List[Choice]:
        """Decide what actions are available given a save state (SaveState -> Action)"""
        print(f"decide_action called for turn {save_state.current_turn}")
        
        if self.decide_end(save_state):
            print("Game has ended, returning empty choices")
            return []
        
        turn_index = save_state.current_turn - 1
        print(f"Turn index: {turn_index}, TURN_ACTIONS length: {len(TURN_ACTIONS)}")
        
        if turn_index >= len(TURN_ACTIONS):
            print("Turn index out of bounds")
            return []
        
        action = TURN_ACTIONS[turn_index]
        print(f"Action for turn {save_state.current_turn}: {action}")
        
        if action == 'border':
            print("Border turn, returning empty choices")
            return []  # No tile choices during border drawing turns
        
        # Generate available choices based on current game state
        available_choices = self.generate_choice()
        print(f"Generated {len(available_choices)} choices")
        return available_choices
    
    def decide_end(self, save_state: SaveState) -> bool:
        """Decide if the game has ended given a save state (SaveState -> boolean)"""
        # Game ends after the last turn
        return save_state.current_turn > len(TURN_ACTIONS)
    
    def calculate_points(self, save_state: SaveState) -> int:
        """Calculate points given a save state (SaveState -> integer)"""
        if not self.decide_end(save_state):
            return 0  # Don't calculate points until game is over
        points = 0
        for tile in save_state.placed_tiles:
            tile_points = self._calculate_tile_points(tile, save_state)
            points += tile_points
        # Calculate penalty for features in wrong locations (sea vs island)
        points -= self._calculate_location_penalties(save_state)
        return points
    
    def _calculate_tile_points(self, placed_tile: PlacedTile, save_state: SaveState) -> int:
        """Calculate points for a single placed tile based on game rules"""
        tile_type = placed_tile.choice.tile_type
        position = placed_tile.tile_position
        
        if tile_type == "ships":
            return self._calculate_ship_points(position, save_state)
        elif tile_type == "waves":
            return self._calculate_wave_points(position, save_state)
        elif tile_type == "beach":
            return self._calculate_beach_points(position, save_state)
        elif tile_type == "houses":
            return self._calculate_house_points(position, save_state)
        elif tile_type == "churches":
            return self._calculate_church_points(position, save_state)
        elif tile_type == "forest":
            return self._calculate_forest_points(position, save_state)
        elif tile_type == "mountain":
            return self._calculate_mountain_points(position, save_state)
        else:
            return 0
    
    def _get_adjacent_positions(self, position: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Get the 4 orthogonal adjacent positions (touching)"""
        x, y = position
        adjacent = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            new_x, new_y = x + dx, y + dy
            if 0 <= new_x < self.grid_size and 0 <= new_y < self.grid_size:
                adjacent.append((new_x, new_y))
        return adjacent
    
    def _get_nearby_positions(self, position: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Get the 8 surrounding positions (near)"""
        x, y = position
        nearby = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                new_x, new_y = x + dx, y + dy
                if 0 <= new_x < self.grid_size and 0 <= new_y < self.grid_size:
                    nearby.append((new_x, new_y))
        return nearby
    
    def _get_tile_at_position(self, position: Tuple[int, int], save_state: SaveState) -> Optional[PlacedTile]:
        """Get the tile at a specific position"""
        for tile in save_state.placed_tiles:
            if tile.tile_position == position:
                return tile
        return None
    
    def _is_on_island(self, position: Tuple[int, int], save_state: SaveState) -> bool:
        """Check if a position is on an island"""
        for island in save_state.islands:
            if position in island.enclosed_positions:
                return True
        return False
    
    def _is_on_same_island(self, pos1: Tuple[int, int], pos2: Tuple[int, int], save_state: SaveState) -> bool:
        """Check if two positions are on the same island"""
        for island in save_state.islands:
            if pos1 in island.enclosed_positions and pos2 in island.enclosed_positions:
                return True
        return False
    
    def _calculate_ship_points(self, position: Tuple[int, int], save_state: SaveState) -> int:
        """Ships like to be far from islands and other boats (1pt per square separation)"""
        # If ship is on an island, it scores 0 points
        if self._is_on_island(position, save_state):
            return 0
            
        min_distance = float('inf')
        
        # Find minimum distance to any other ship or island
        for tile in save_state.placed_tiles:
            # Skip the ship itself
            if tile.tile_position == position:
                continue
                
            is_on_island = self._is_on_island(tile.tile_position, save_state)
            
            if tile.choice.tile_type == "ships" or is_on_island:
                distance = abs(position[0] - tile.tile_position[0]) + abs(position[1] - tile.tile_position[1])
                min_distance = min(min_distance, distance)
        
        # Also check all empty tiles on islands
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                empty_pos = (x, y)
                # Skip if this is the ship's position
                if empty_pos == position:
                    continue
                # Skip if there's already a tile here (we checked placed tiles above)
                if any(tile.tile_position == empty_pos for tile in save_state.placed_tiles):
                    continue
                # Check if this empty position is on an island
                if self._is_on_island(empty_pos, save_state):
                    distance = abs(position[0] - empty_pos[0]) + abs(position[1] - empty_pos[1])
                    min_distance = min(min_distance, distance)
        
        return int(min_distance) if min_distance != float('inf') else 0
    
    def _calculate_wave_points(self, position: Tuple[int, int], save_state: SaveState) -> int:
        """Waves don't like to be near other waves or in same row/column (2pts for each following rules)"""
        x, y = position
        
        # Check if this wave follows the rules
        follows_rules = True
        
        # Check for other waves in same row or column
        for tile in save_state.placed_tiles:
            if tile.choice.tile_type == "waves" and tile.tile_position != position:
                tx, ty = tile.tile_position
                if tx == x or ty == y:  # Same row or column
                    follows_rules = False
                    break
        
        # Check for nearby waves
        nearby = self._get_nearby_positions(position)
        for pos in nearby:
            tile = self._get_tile_at_position(pos, save_state)
            if tile and tile.choice.tile_type == "waves":
                follows_rules = False
                break
        
        return 2 if follows_rules else 0
    
    def _calculate_beach_points(self, position: Tuple[int, int], save_state: SaveState) -> int:
        """Beach likes to touch island shores but not be on island (1pt per touching side)"""
        points = 0
        adjacent = self._get_adjacent_positions(position)
        
        for adj_pos in adjacent:
            if self._is_on_island(adj_pos, save_state):
                points += 1
        
        return points
    
    def _calculate_house_points(self, position: Tuple[int, int], save_state: SaveState) -> int:
        """Houses like to be near different things but not other houses (1pt per unique feature)"""
        unique_features = set()
        nearby = self._get_nearby_positions(position)
        
        for pos in nearby:
            tile = self._get_tile_at_position(pos, save_state)
            if tile and tile.choice.tile_type != "houses":
                unique_features.add(tile.choice.tile_type)
        
        return len(unique_features)
    
    def _calculate_church_points(self, position: Tuple[int, int], save_state: SaveState) -> int:
        """Churches like houses on same island but not another church (2pts per nearby house, 1pt per additional house on island, 0 if another church on island)"""
        if self._has_another_church_on_island(position, save_state):
            return 0

        points = 0
        nearby_houses = set()
        all_houses_on_island = set()

        # 1. Add 2 points for each nearby house
        for pos in self._get_nearby_positions(position):
            tile = self._get_tile_at_position(pos, save_state)
            if tile and tile.choice.tile_type == "houses":
                points += 2
                nearby_houses.add(pos)

        # 2. Add 1 point for each house on the same island (excluding already counted nearby houses)
        for tile in save_state.placed_tiles:
            if tile.choice.tile_type == "houses" and self._is_on_same_island(position, tile.tile_position, save_state):
                if tile.tile_position not in nearby_houses:
                    points += 1

        return points
    
    def _calculate_forest_points(self, position: Tuple[int, int], save_state: SaveState) -> int:
        """Forest likes to touch other forest - group scoring: (n-1)*2 points for group of n forests"""
        # Get the forest group this forest belongs to
        forest_group = self._get_forest_group(position, save_state)
        
        # If this is a single forest (not connected to others), score 0
        if len(forest_group) <= 1:
            return 0
        
        # Calculate total points for the group: (n-1) * 2
        total_group_points = (len(forest_group) - 1) * 2
        
        # Distribute points equally among all forests in the group
        base_points_per_forest = total_group_points // len(forest_group)
        remainder = total_group_points % len(forest_group)
        
        # Add extra point for the first 'remainder' forests to distribute leftover points
        forest_index = sorted(forest_group).index(position)
        if forest_index < remainder:
            return base_points_per_forest + 1
        else:
            return base_points_per_forest
    
    def _calculate_mountain_points(self, position: Tuple[int, int], save_state: SaveState) -> int:
        """Mountain likes to be near forest (2pts per forest nearby)"""
        points = 0
        nearby = self._get_nearby_positions(position)
        
        for pos in nearby:
            tile = self._get_tile_at_position(pos, save_state)
            if tile and tile.choice.tile_type == "forest":
                points += 2
        
        return points
    
    def _has_another_church_on_island(self, position: Tuple[int, int], save_state: SaveState) -> bool:
        """Check if there's another church on the same island"""
        for tile in save_state.placed_tiles:
            if (tile.choice.tile_type == "churches" and 
                tile.tile_position != position and 
                self._is_on_same_island(position, tile.tile_position, save_state)):
                return True
        return False
    
    def _get_forest_group(self, position: Tuple[int, int], save_state: SaveState) -> Set[Tuple[int, int]]:
        """Get all connected forest tiles"""
        visited = set()
        group = set()
        self._dfs_forest(position, save_state, visited, group)
        return group
    
    def _dfs_forest(self, position: Tuple[int, int], save_state: SaveState, 
                   visited: Set[Tuple[int, int]], group: Set[Tuple[int, int]]):
        """Depth-first search to find connected forest tiles"""
        if position in visited:
            return
        
        visited.add(position)
        tile = self._get_tile_at_position(position, save_state)
        if not tile or tile.choice.tile_type != "forest":
            return
        
        group.add(position)
        adjacent = self._get_adjacent_positions(position)
        for adj_pos in adjacent:
            self._dfs_forest(adj_pos, save_state, visited, group)
    
    def _calculate_location_penalties(self, save_state: SaveState) -> int:
        """Calculate penalties for features in wrong locations (5pts per violation)"""
        penalties = 0
        
        for tile in save_state.placed_tiles:
            if self._is_feature_in_wrong_location(tile, save_state):
                penalties += 5
        
        return penalties
    
    def _is_feature_in_wrong_location(self, tile: PlacedTile, save_state: SaveState) -> bool:
        """Check if a feature is in the wrong location (sea vs island)"""
        tile_type = tile.choice.tile_type
        position = tile.tile_position
        is_on_island = self._is_on_island(position, save_state)
        
        # Sea features that should be on islands
        if tile_type in ["houses", "churches", "forest", "mountain"] and not is_on_island:
            return True
        
        # Island features that should be in the sea
        if tile_type in ["ships", "waves"] and is_on_island:
            return True
        
        # Beach should be touching islands but not on them
        if tile_type == "beach" and is_on_island:
            return True
        
        return False
    

    
    def generate_bounded_tile_pool(self):
        TILE_TYPES = ['beach', 'churches', 'forest', 'houses', 'mountain', 'ships', 'waves']
        MIN_COUNTS = [8, 4, 11, 8, 3, 3, 8]
        MAX_COUNTS = [9, 6, 13, 11, 5, 3, 10]
        TOTAL = 52
        counts = MIN_COUNTS[:]
        remaining = TOTAL - sum(counts)
        indices = list(range(len(TILE_TYPES)))
        while remaining > 0:
            random.shuffle(indices)
            for i in indices:
                if counts[i] < MAX_COUNTS[i]:
                    counts[i] += 1
                    remaining -= 1
                    if remaining == 0:
                        break
        pool = []
        for tile, count in zip(TILE_TYPES, counts):
            pool.extend([tile] * count)
        random.shuffle(pool)
        return pool
    
    def generate_choice(self) -> List[Choice]:
        """Generate exactly 2 random choices for the current turn, using the bounded tile type pool."""
        choices = []
        chunk_types = [chunk.value for chunk in ChunkType]
        max_attempts = 100
        attempts = 0
        # Draw tile types from the pool
        if self.tile_type_pool_index + 2 > len(self.tile_type_pool):
            raise ValueError("Not enough tile types left in the pool for this game!")
        tile_type1 = self.tile_type_pool[self.tile_type_pool_index]
        tile_type2 = self.tile_type_pool[self.tile_type_pool_index + 1]
        self.tile_type_pool_index += 2
        chunk_type1 = random.choice(chunk_types)
        chunk_position1 = random.randint(1, 9)
        first_choice = Choice(
            tile_type=tile_type1,
            chunk_type=chunk_type1,
            chunk_position=chunk_position1
        )
        choices.append(first_choice)
        # Ensure the second choice is different in tile type or chunk position
        while attempts < max_attempts:
            chunk_type2 = random.choice(chunk_types)
            chunk_position2 = random.randint(1, 9)
            second_choice = Choice(
                tile_type=tile_type2,
                chunk_type=chunk_type2,
                chunk_position=chunk_position2
            )
            if (second_choice.tile_type != first_choice.tile_type or
                second_choice.chunk_position != first_choice.chunk_position):
                choices.append(second_choice)
                break
            attempts += 1
        if len(choices) == 1:
            # Force a different choice by changing at least one property
            if first_choice.chunk_position < 9:
                second_choice = Choice(
                    tile_type=first_choice.tile_type,
                    chunk_type=first_choice.chunk_type,
                    chunk_position=first_choice.chunk_position + 1
                )
            else:
                second_choice = Choice(
                    tile_type=first_choice.tile_type,
                    chunk_type=first_choice.chunk_type,
                    chunk_position=first_choice.chunk_position - 1
                )
            choices.append(second_choice)
        # Debug: track generated tile types
        self.generated_tile_types_debug.append(first_choice.tile_type)
        self.generated_tile_types_debug.append(choices[1].tile_type)
        return choices
    
    def _validate_border_tiles(self, tile_positions: List[Tuple[int, int]]) -> bool:
        """Validate that a set of tile positions forms a valid enclosed area"""
        if not tile_positions:
            return False
        
        # Check that all tiles are neighbors (connected)
        if not self._are_tiles_connected(tile_positions):
            return False
        
        # Check that the area is properly enclosed
        if not self._is_area_enclosed(tile_positions):
            return False
        
        # Check that the border length is <= 24 units
        border_length = self._calculate_border_length(tile_positions)
        if border_length > MAX_BORDER_LINES:
            return False
        
        return True
    
    def _are_tiles_connected(self, tile_positions: List[Tuple[int, int]]) -> bool:
        """Check if all tiles are connected (neighbors)"""
        if len(tile_positions) <= 1:
            return True
        
        # Use BFS to check connectivity
        visited = set()
        queue = [tile_positions[0]]
        visited.add(tile_positions[0])
        
        while queue:
            current = queue.pop(0)
            # Check all 4 adjacent positions
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor = (current[0] + dx, current[1] + dy)
                if neighbor in tile_positions and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        
        return len(visited) == len(tile_positions)
    
    def _calculate_border_length(self, tile_positions: List[Tuple[int, int]]) -> int:
        """Calculate the length of the border around the tile positions"""
        if not tile_positions:
            return 0
        
        tile_set = set(tile_positions)
        border_edges = set()  # Use set to avoid counting edges twice
        
        for pos in tile_positions:
            x, y = pos  # x is column, y is row
            # Check each of the 4 sides of this tile
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor = (x + dx, y + dy)
                # If neighbor is not in our tile set, this is a border edge
                if neighbor not in tile_set:
                    # Create a unique identifier for this edge to avoid double counting
                    # Use a consistent representation for each edge
                    if dx == 0:  # Vertical edge
                        edge = tuple(sorted([(x, y), (x, y + 1)])) if dy < 0 else tuple(sorted([(x, y + 1), (x, y)]))
                    else:  # Horizontal edge
                        edge = tuple(sorted([(x, y), (x + 1, y)])) if dx < 0 else tuple(sorted([(x + 1, y), (x, y)]))
                    border_edges.add(edge)
        
        return len(border_edges)
    
    def _is_area_enclosed(self, tile_positions: List[Tuple[int, int]]) -> bool:
        """Check if the area is properly enclosed (no holes, forms a single connected region)"""
        if len(tile_positions) <= 1:
            return True
        
        # Create a set for fast lookup
        tile_set = set(tile_positions)
        
        # Find the bounding box
        min_x = min(pos[0] for pos in tile_positions)  # x is column
        max_x = max(pos[0] for pos in tile_positions)
        min_y = min(pos[1] for pos in tile_positions)  # y is row
        max_y = max(pos[1] for pos in tile_positions)
        
        # Check that all tiles within the bounding box are either in the set or outside
        # This ensures no holes in the middle
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                pos = (x, y)
                if pos not in tile_set:
                    # This position is not in our tile set
                    # Check if it's completely surrounded by our tiles (indicating a hole)
                    if self._is_position_surrounded(pos, tile_set):
                        return False
        
        return True
    
    def _is_position_surrounded(self, pos: Tuple[int, int], tile_set: set) -> bool:
        """Check if a position is completely surrounded by tiles in the set"""
        x, y = pos  # x is column, y is row
        # Check all 4 adjacent positions
        adjacent_count = 0
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            neighbor = (x + dx, y + dy)
            if neighbor in tile_set:
                adjacent_count += 1
        
        # If it's surrounded by 4 tiles, it's a hole
        return adjacent_count == 4
    
    def _tiles_to_border_lines(self, tile_positions: List[Tuple[int, int]]) -> List[BorderLine]:
        """Convert tile positions to border lines for storage"""
        if not tile_positions:
            return []
        
        tile_set = set(tile_positions)
        border_lines = []
        
        for pos in tile_positions:
            x, y = pos  # x is column, y is row
            # Check each of the 4 sides of this tile
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor = (x + dx, y + dy)
                # If neighbor is not in our tile set, this is a border edge
                if neighbor not in tile_set:
                    # Create a border line for this edge
                    if dx == 0:  # Vertical edge
                        # Vertical line between this tile and neighbor
                        start_pos = (x, y) if dy < 0 else (x, y + 1)
                        end_pos = (x + 1, y) if dy < 0 else (x + 1, y + 1)
                        border_line = BorderLine(start_pos, end_pos, False)
                    else:  # Horizontal edge
                        # Horizontal line between this tile and neighbor
                        start_pos = (x, y) if dx < 0 else (x + 1, y)
                        end_pos = (x, y + 1) if dx < 0 else (x + 1, y + 1)
                        border_line = BorderLine(start_pos, end_pos, True)
                    
                    # Only add if we haven't already added this line (avoid duplicates)
                    if not any(self._lines_equal(border_line, existing) for existing in border_lines):
                        border_lines.append(border_line)
        
        return border_lines
    
    def _lines_equal(self, line1: BorderLine, line2: BorderLine) -> bool:
        """Check if two border lines are equal (same edge)"""
        return ((line1.start_pos == line2.start_pos and line1.end_pos == line2.end_pos) or
                (line1.start_pos == line2.end_pos and line1.end_pos == line2.start_pos))

    def make_turn(self, save_state: SaveState, chosen_choice: Choice, 
                  discarded_choice: Choice, tile_position: Tuple[int, int],
                  border_tiles: Optional[List[Tuple[int, int]]] = None) -> SaveState:
        """Make a turn and return the updated save state"""
        if self.decide_end(save_state):
            raise ValueError("Cannot make turn: game has ended")
        
        # Create new save state
        new_save_state = copy.deepcopy(save_state)
        
        # Create turn history
        chosen_tile = PlacedTile(chosen_choice, tile_position)
        discarded_tile = PlacedTile(discarded_choice, tile_position)
        
        # Handle border turn vs tile placement turn
        turn_index = save_state.current_turn - 1
        if TURN_ACTIONS[turn_index] == 'border':
            # Border drawing turn - validate and process tile positions
            if border_tiles:
                # Validate the border tiles
                if not self._validate_border_tiles(border_tiles):
                    raise ValueError("Invalid border tiles: must be connected, enclosed, and have border length <= 24")
                
                # Convert tiles to border lines for storage
                border_lines = self._tiles_to_border_lines(border_tiles)
                
                # Store previous island positions for comparison
                prev_island_positions = set()
                for island in save_state.islands:
                    prev_island_positions.update(island.enclosed_positions)
                
                # Add new border lines to the state
                new_save_state.border_lines.extend(border_lines)
                
                # Create island from the tile positions
                is_lake = len(border_tiles) < 10  # Arbitrary threshold for now
                new_island = Island(
                    border_lines=border_lines,
                    enclosed_positions=set(border_tiles),
                    is_lake=is_lake
                )
                new_save_state.islands.append(new_island)
                
                # Update turn history with border lines
                turn_history = TurnHistory(
                    chosen_tile=chosen_tile,
                    discarded_tile=discarded_tile,
                    border_lines=border_lines
                )
            else:
                # No border tiles provided
                turn_history = TurnHistory(
                    chosen_tile=chosen_tile,
                    discarded_tile=discarded_tile,
                    border_lines=[]
                )
        else:
            # Tile placement turn
            new_save_state.placed_tiles.append(chosen_tile)
            turn_history = TurnHistory(
                chosen_tile=chosen_tile,
                discarded_tile=discarded_tile,
                border_lines=[]
            )
        
        # Update save state
        new_save_state.choice_history.append(turn_history)
        new_save_state.current_turn += 1
        
        return new_save_state
    
    def get_game_summary(self, save_state: SaveState) -> Dict[str, Any]:
        """Get a summary of the current game state"""
        turn_index = save_state.current_turn - 1
        phase = TURN_ACTIONS[turn_index] if turn_index < len(TURN_ACTIONS) else 'ended'
        cycle = (save_state.current_turn - 1) // 10 + 1 if save_state.current_turn <= len(TURN_ACTIONS) else 3
        summary = {
            "game_id": save_state.game_id,
            "current_turn": save_state.current_turn,
            "total_turns": len(TURN_ACTIONS),
            "total_turns_played": len(save_state.choice_history),
            "current_points": self.calculate_points(save_state),
            "game_ended": self.decide_end(save_state),
            "created_at": save_state.created_at,
            "tiles_placed": len(save_state.placed_tiles),
            "border_lines_drawn": len(save_state.border_lines),
            "islands_formed": len(save_state.islands),
            "phase": phase,
            "cycle": cycle,
            "turns_in_cycle": (save_state.current_turn - 1) % 10 + 1 if save_state.current_turn <= len(TURN_ACTIONS) else 10
        }
        # Debug: print tile type list at end of game
        if summary['game_ended'] and not self.tile_type_list_printed:
            print("\n[DEBUG] Tile types for all choices this game:")
            print(self.generated_tile_types_debug)
            self.tile_type_list_printed = True
        return summary


# Example usage and testing
if __name__ == "__main__":
    # Create a new game
    game_runner = GameRunner()
    save_state = game_runner.create_new_game()
    
    print("=== TINY ISLANDS GAME TEST ===")
    print(f"New game created: {save_state.game_id}")
    print(f"Game structure: 9 choice turns + 1 border turn, repeated 3 times (30 total turns)")
    print()
    
    # Simulate several turns to show progression
    for turn in range(1, 12):  # Test through turn 11
        print(f"--- Turn {turn} ---")
        
        # Get game summary
        summary = game_runner.get_game_summary(save_state)
        print(f"Phase: {summary['phase']}, Cycle: {summary['cycle']}, Turn in cycle: {summary['turns_in_cycle']}")
        
        if summary['phase'] == 'choice':
            # Make a tile placement turn
            available_actions = game_runner.decide_action(save_state)
            if available_actions:
                chosen = available_actions[0]
                discarded = available_actions[1] if len(available_actions) > 1 else available_actions[0]
                
                save_state = game_runner.make_turn(
                    save_state, 
                    chosen, 
                    discarded, 
                    (turn % 9, (turn * 2) % 9)  # Vary positions (x, y)
                )
                print(f"Placed {chosen.tile_type} tile at position ({turn % 9}, {(turn * 2) % 9})")
        else:
            # Border drawing turn
            border_tiles = [
                (0, 0), (0, 1), (0, 2), (1, 2), (2, 2), (2, 1), (2, 0), (1, 0)  # Valid enclosed area
            ]
            save_state = game_runner.make_turn(
                save_state,
                Choice("houses", "cluster", 1),  # Dummy choice for border turn
                Choice("ships", "cluster", 2),   # Dummy choice for border turn
                (0, 0),  # Dummy position
                border_tiles
            )
            print(f"Drew {len(border_tiles)} border tiles")
        
        print(f"Tiles placed: {summary['tiles_placed']}, Border lines: {summary['border_lines_drawn']}")
        print(f"Current points: {summary['current_points']}")
        print()
    
    print("=== FINAL GAME STATE ===")
    final_summary = game_runner.get_game_summary(save_state)
    print(json.dumps(final_summary, indent=2))
    
    # Save to file
    save_state.save_to_file("test_save.json")
    print("\nSave state saved to test_save.json") 