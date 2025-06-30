from typing import List, Dict, Tuple, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import json
import copy
from datetime import datetime
import random


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
    'choice', 'choice', 'choice', 'choice', 'choice', 'choice', 'choice', 'choice', 'choice', 'border'
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
    
    def create_new_game(self) -> SaveState:
        """Create a new game save state"""
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
        
        # Calculate points based on placed tiles
        for tile in save_state.placed_tiles:
            points += self._calculate_tile_points(tile, save_state)
        
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
        min_distance = float('inf')
        
        # Find minimum distance to any other ship or island
        for tile in save_state.placed_tiles:
            if tile.choice.tile_type == "ships" or self._is_on_island(tile.tile_position, save_state):
                distance = abs(position[0] - tile.tile_position[0]) + abs(position[1] - tile.tile_position[1])
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
        # Check if another church is on the same island
        if self._has_another_church_on_island(position, save_state):
            return 0
        
        points = 0
        nearby = self._get_nearby_positions(position)
        houses_on_island = 0
        
        for pos in nearby:
            tile = self._get_tile_at_position(pos, save_state)
            if tile and tile.choice.tile_type == "houses":
                points += 2  # 2pts for each nearby house
                if self._is_on_same_island(position, pos, save_state):
                    houses_on_island += 1
        
        # Add 1pt for each additional house on the same island
        points += houses_on_island
        
        return points
    
    def _calculate_forest_points(self, position: Tuple[int, int], save_state: SaveState) -> int:
        """Forest likes to touch other forest (2pts per forest in group minus 2pts)"""
        forest_group = self._get_forest_group(position, save_state)
        return 2 * len(forest_group) - 2
    
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
    
    def _detect_islands(self, border_lines: List[BorderLine]) -> List[Island]:
        """Detect islands and lakes from border lines"""
        if not border_lines:
            return []
        
        # Create a grid representation of the border lines
        grid = [[False for _ in range(self.grid_size + 1)] for _ in range(self.grid_size + 1)]
        
        # Mark border lines on the grid
        for line in border_lines:
            start_row, start_col = line.start_pos
            end_row, end_col = line.end_pos
            
            if line.is_horizontal:
                # Horizontal line
                for col in range(min(start_col, end_col), max(start_col, end_col) + 1):
                    grid[start_row][col] = True
            else:
                # Vertical line
                for row in range(min(start_row, end_row), max(start_row, end_row) + 1):
                    grid[row][start_col] = True
        
        # Find enclosed areas using flood-fill
        islands = []
        visited = set()
        
        for row in range(self.grid_size + 1):
            for col in range(self.grid_size + 1):
                if (row, col) not in visited and not grid[row][col]:
                    # Found an unvisited non-border position
                    enclosed_positions = set()
                    self._flood_fill(row, col, grid, visited, enclosed_positions)
                    
                    if enclosed_positions:
                        # Convert enclosed positions to tile positions
                        tile_positions = set()
                        for pos in enclosed_positions:
                            # Convert vertex positions to tile positions
                            if pos[0] < self.grid_size and pos[1] < self.grid_size:
                                tile_positions.add(pos)
                        
                        if tile_positions:
                            # Determine if this is a lake (enclosed within existing islands)
                            is_lake = self._is_lake(tile_positions)
                            island = Island(
                                border_lines=border_lines,
                                enclosed_positions=tile_positions,
                                is_lake=is_lake
                            )
                            islands.append(island)
        
        return islands
    
    def _flood_fill(self, row: int, col: int, grid: List[List[bool]], 
                   visited: Set[Tuple[int, int]], enclosed_positions: Set[Tuple[int, int]]):
        """Flood fill to find enclosed areas"""
        if (row < 0 or row >= len(grid) or col < 0 or col >= len(grid[0]) or
            (row, col) in visited or grid[row][col]):
            return
        
        visited.add((row, col))
        enclosed_positions.add((row, col))
        
        # Recursively fill adjacent positions
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            self._flood_fill(row + dr, col + dc, grid, visited, enclosed_positions)
    
    def _is_lake(self, tile_positions: Set[Tuple[int, int]]) -> bool:
        """Determine if an enclosed area is a lake (within an existing island)"""
        # For now, we'll consider it a lake if it's a small enclosed area
        # In a full implementation, you'd check if it's completely surrounded by existing islands
        return len(tile_positions) < 10  # Arbitrary threshold for now
    
    def generate_choice(self) -> List[Choice]:
        """Generate exactly 2 random choices for the current turn"""
        choices = []
        
        # Generate random tile types and chunk types
        tile_types = [tile.value for tile in TileType]
        chunk_types = [chunk.value for chunk in ChunkType]
        
        # Generate exactly 2 random choices
        for _ in range(2):
            tile_type = random.choice(tile_types)
            chunk_type = random.choice(chunk_types)
            chunk_position = random.randint(1, 9)  # Random position within chunk
            
            choices.append(Choice(
                tile_type=tile_type,
                chunk_type=chunk_type,
                chunk_position=chunk_position
            ))
        
        return choices
    
    def make_turn(self, save_state: SaveState, chosen_choice: Choice, 
                  discarded_choice: Choice, tile_position: Tuple[int, int],
                  border_lines: Optional[List[BorderLine]] = None) -> SaveState:
        """Make a turn and return the updated save state"""
        if self.decide_end(save_state):
            raise ValueError("Cannot make turn: game has ended")
        
        # Create new save state
        new_save_state = copy.deepcopy(save_state)
        
        # Create turn history
        chosen_tile = PlacedTile(chosen_choice, tile_position)
        discarded_tile = PlacedTile(discarded_choice, tile_position)
        turn_history = TurnHistory(
            chosen_tile=chosen_tile,
            discarded_tile=discarded_tile,
            border_lines=border_lines if border_lines is not None else []
        )
        
        # Update save state
        new_save_state.choice_history.append(turn_history)
        
        # Handle border turn vs tile placement turn
        turn_index = save_state.current_turn - 1
        if TURN_ACTIONS[turn_index] == 'border':
            # Border drawing turn
            if border_lines:
                new_save_state.border_lines.extend(border_lines)
                # Detect new islands from the border lines
                new_islands = self._detect_islands(border_lines)
                new_save_state.islands.extend(new_islands)
        else:
            # Tile placement turn
            new_save_state.placed_tiles.append(chosen_tile)
        
        new_save_state.current_turn += 1
        
        return new_save_state
    
    def get_game_summary(self, save_state: SaveState) -> Dict[str, Any]:
        """Get a summary of the current game state"""
        turn_index = save_state.current_turn - 1
        phase = TURN_ACTIONS[turn_index] if turn_index < len(TURN_ACTIONS) else 'ended'
        cycle = (save_state.current_turn - 1) // 10 + 1 if save_state.current_turn <= len(TURN_ACTIONS) else 3
        return {
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
                    (turn % 9, (turn * 2) % 9)  # Vary positions
                )
                print(f"Placed {chosen.tile_type} tile at position ({turn % 9}, {(turn * 2) % 9})")
        else:
            # Border drawing turn
            border_lines = [
                BorderLine((0, 0), (8, 0), True),  # Top border
                BorderLine((0, 0), (0, 8), False)  # Left border
            ]
            save_state = game_runner.make_turn(
                save_state,
                Choice("houses", "cluster", 1),  # Dummy choice for border turn
                Choice("ships", "cluster", 2),   # Dummy choice for border turn
                (0, 0),  # Dummy position
                border_lines
            )
            print(f"Drew {len(border_lines)} border lines")
        
        print(f"Tiles placed: {summary['tiles_placed']}, Border lines: {summary['border_lines_drawn']}")
        print(f"Current points: {summary['current_points']}")
        print()
    
    print("=== FINAL GAME STATE ===")
    final_summary = game_runner.get_game_summary(save_state)
    print(json.dumps(final_summary, indent=2))
    
    # Save to file
    save_state.save_to_file("test_save.json")
    print("\nSave state saved to test_save.json") 