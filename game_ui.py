import pygame
import sys
import os
from typing import List, Tuple, Optional
from game import GameRunner, SaveState, Choice, BorderLine, TURN_ACTIONS, GRID_SIZE, MAX_BORDER_LINES

# === PYGAME CONSTANTS ===
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
GRID_CELL_SIZE = 60
GRID_OFFSET_X = 350
GRID_OFFSET_Y = 100
CHOICE_PANEL_WIDTH = 400
CHOICE_PANEL_X = WINDOW_WIDTH - CHOICE_PANEL_WIDTH - 20

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
LIGHT_BLUE = (173, 216, 230)
LIGHT_GREEN = (144, 238, 144)
YELLOW = (255, 255, 0)
RED = (255, 0, 0)
ORANGE = (255, 165, 0)
DARK_GREEN = (0, 100, 0)
BLUE = (0, 0, 255)

# === TILE TYPE ICON PATHS ===
TILE_ICONS = {
    "houses": "icons/houses.png",
    "waves": "icons/waves.png", 
    "ships": "icons/ships.png",
    "forest": "icons/forest.png",
    "mountain": "icons/mountain.png",
    "churches": "icons/churches.png",
    "beach": "icons/beach.png"
}

class GameUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Tiny Islands")
        self.clock = pygame.time.Clock()
        
        # Load and cache tile icons
        self.tile_icons = {}
        self.load_tile_icons()
        
        # Game controller
        self.game_runner = GameRunner()
        self.save_state = self.game_runner.create_new_game()
        
        # UI state
        self.selected_choice: Optional[Choice] = None
        self.discarded_choice: Optional[Choice] = None
        self.current_border_lines: List[BorderLine] = []
        self.current_choices: Optional[List[Choice]] = None
        self.choice_locked: bool = False
        
        # Border drawing state
        self.border_drag_start: Optional[Tuple[int, int]] = None
        self.border_drag_path: List[Tuple[int, int]] = []
        self.border_drag_active = False
        self.border_nodes: List[Tuple[int, int]] = []
        
        # Hover state
        self.hover_choice: Optional[Choice] = None
        self.hover_position: Optional[Tuple[int, int]] = None
        self.mouse_pos = (0, 0)
        
        # Initialize border nodes
        self.initialize_border_nodes()
        
        # Fonts - Made bigger
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 32)
        self.font_small = pygame.font.Font(None, 24)
        
        self.colored_island_tiles = set()  # Stores all tiles that have ever been part of an island
    
    def load_tile_icons(self):
        """Load and resize tile icons"""
        for tile_type, icon_path in TILE_ICONS.items():
            try:
                if os.path.exists(icon_path):
                    # Load and resize icon
                    image = pygame.image.load(icon_path)
                    image = pygame.transform.scale(image, (GRID_CELL_SIZE, GRID_CELL_SIZE))
                    self.tile_icons[tile_type] = image
                else:
                    # Create a placeholder
                    self.create_placeholder_icon(tile_type)
            except Exception as e:
                print(f"Error loading icon for {tile_type}: {e}")
                self.create_placeholder_icon(tile_type)
    
    def create_placeholder_icon(self, tile_type: str):
        """Create a placeholder icon"""
        surface = pygame.Surface((GRID_CELL_SIZE, GRID_CELL_SIZE))
        surface.fill(LIGHT_GRAY)
        # Add text
        text = self.font_small.render(tile_type[:3].upper(), True, BLACK)
        text_rect = text.get_rect(center=(GRID_CELL_SIZE//2, GRID_CELL_SIZE//2))
        surface.blit(text, text_rect)
        self.tile_icons[tile_type] = surface
    
    def initialize_border_nodes(self):
        """Initialize the border nodes (tile vertices/corners)"""
        self.border_nodes = []
        # Create nodes at each tile vertex (corner)
        for row in range(GRID_SIZE + 1):
            for col in range(GRID_SIZE + 1):
                self.border_nodes.append((row, col))
    
    def get_grid_pos_from_mouse(self, mouse_pos: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        """Convert mouse position to grid position"""
        x, y = mouse_pos
        if (GRID_OFFSET_X <= x < GRID_OFFSET_X + GRID_SIZE * GRID_CELL_SIZE and
            GRID_OFFSET_Y <= y < GRID_OFFSET_Y + GRID_SIZE * GRID_CELL_SIZE):
            grid_x = (x - GRID_OFFSET_X) // GRID_CELL_SIZE  # Column
            grid_y = (y - GRID_OFFSET_Y) // GRID_CELL_SIZE  # Row
            return (grid_x, grid_y)  # Return (x, y) where x is column, y is row
        return None
    
    def get_vertex_pos_from_mouse(self, mouse_pos: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        """Convert mouse position to vertex position (tile corner)"""
        x, y = mouse_pos
        if (GRID_OFFSET_X <= x < GRID_OFFSET_X + (GRID_SIZE + 1) * GRID_CELL_SIZE and
            GRID_OFFSET_Y <= y < GRID_OFFSET_Y + (GRID_SIZE + 1) * GRID_CELL_SIZE):
            # Calculate which vertex the mouse is closest to
            vertex_x = round((x - GRID_OFFSET_X) / GRID_CELL_SIZE)  # Column
            vertex_y = round((y - GRID_OFFSET_Y) / GRID_CELL_SIZE)  # Row
            
            # Clamp to valid range
            vertex_x = max(0, min(GRID_SIZE, vertex_x))
            vertex_y = max(0, min(GRID_SIZE, vertex_y))
            
            return (vertex_x, vertex_y)  # Return (x, y) where x is column, y is row
        return None
    
    def is_border_turn(self) -> bool:
        """Check if current turn is a border drawing turn"""
        summary = self.game_runner.get_game_summary(self.save_state)
        return summary['phase'] == 'border'
    
    def get_chunk_positions(self, choice: Choice) -> List[Tuple[int, int]]:
        """Get the valid positions for a given chunk"""
        positions = []
        chunk_type = choice.chunk_type
        chunk_position = choice.chunk_position
        
        if chunk_type == "cluster":
            # 3x3 clusters, numbered 1-9 from top-left to bottom-right
            cluster_y = ((chunk_position - 1) // 3) * 3  # Row
            cluster_x = ((chunk_position - 1) % 3) * 3   # Column
            for y in range(cluster_y, cluster_y + 3):
                for x in range(cluster_x, cluster_x + 3):
                    positions.append((x, y))  # (x, y) where x is column, y is row
        
        elif chunk_type == "horizontal":
            # Horizontal rows, numbered 1-9 from top to bottom
            y = chunk_position - 1  # Row
            for x in range(GRID_SIZE):  # Columns
                positions.append((x, y))
        
        elif chunk_type == "vertical":
            # Vertical columns, numbered 1-9 from left to right
            x = chunk_position - 1  # Column
            for y in range(GRID_SIZE):  # Rows
                positions.append((x, y))
        
        return positions
    
    def get_tile_at_position(self, position: Tuple[int, int]):
        """Get tile at a specific position"""
        for tile in self.save_state.placed_tiles:
            if tile.tile_position == position:
                return tile
        return None
    
    def get_current_choices(self):
        """Get or generate the current turn's choices"""
        if self.current_choices is None:
            self.current_choices = self.game_runner.decide_action(self.save_state)
        return self.current_choices
    
    def clear_current_choices(self):
        """Clear current choices"""
        self.current_choices = None
        self.selected_choice = None
        self.discarded_choice = None
        self.choice_locked = False
    
    def select_choice(self, choice: Choice):
        """Select a choice"""
        self.selected_choice = choice
        self.discarded_choice = None
        
        # Find the other choice to discard
        available_choices = self.get_current_choices()
        for other_choice in available_choices:
            if other_choice != choice:
                self.discarded_choice = other_choice
                break
    
    def place_tile_at_position(self, position: Tuple[int, int]):
        """Place the selected tile at the given position"""
        if not self.selected_choice or not self.discarded_choice:
            return
        
        try:
            self.save_state = self.game_runner.make_turn(
                self.save_state,
                self.selected_choice,
                self.discarded_choice,
                position
            )
            # Reset selections and choices for next turn
            self.clear_current_choices()
        except ValueError as e:
            print(f"Error placing tile: {e}")
    
    def is_valid_border_path(self, path: List[Tuple[int, int]]) -> bool:
        """Check if a path only contains valid grid-aligned moves"""
        if len(path) < 2:
            return False
        
        for i in range(len(path) - 1):
            start = path[i]
            end = path[i + 1]
            
            # Check if move is horizontal or vertical only
            if start[0] != end[0] and start[1] != end[1]:
                return False
            
            # Check if move is only one step
            if abs(start[0] - end[0]) > 1 or abs(start[1] - end[1]) > 1:
                return False
        
        return True
    
    def is_enclosed_path(self, path: List[Tuple[int, int]]) -> bool:
        """Check if a path forms an enclosed area"""
        if len(path) < 4:
            return False
        return path[0] == path[-1] and len(path) > 3
    
    def create_border_lines_from_path(self, path: List[Tuple[int, int]]) -> List[BorderLine]:
        """Create border lines from a path"""
        border_lines = []
        for i in range(len(path) - 1):
            start = path[i]
            end = path[i + 1]
            
            is_horizontal = start[0] == end[0]
            is_vertical = start[1] == end[1]
            
            if is_horizontal or is_vertical:
                border_line = BorderLine(
                    start_pos=start,
                    end_pos=end,
                    is_horizontal=is_horizontal
                )
                border_lines.append(border_line)
        
        return border_lines
    
    def draw_grid(self):
        """Draw the main game grid"""
        # Draw permanent island backgrounds with the new color #c9c6af
        ISLAND_PERMA_COLOR = (201, 198, 175)  # #c9c6af in RGB
        for (x, y) in self.colored_island_tiles:  # x is column, y is row
            screen_x = GRID_OFFSET_X + x * GRID_CELL_SIZE
            screen_y = GRID_OFFSET_Y + y * GRID_CELL_SIZE
            pygame.draw.rect(self.screen, ISLAND_PERMA_COLOR, (screen_x, screen_y, GRID_CELL_SIZE, GRID_CELL_SIZE))
        
        # Draw grid cells
        for y in range(GRID_SIZE):  # Rows
            for x in range(GRID_SIZE):  # Columns
                screen_x = GRID_OFFSET_X + x * GRID_CELL_SIZE
                screen_y = GRID_OFFSET_Y + y * GRID_CELL_SIZE
                
                # Determine cell color (only for non-island tiles)
                color = WHITE
                tile = self.get_tile_at_position((x, y))  # (x, y) where x is column, y is row
                
                # Only apply cell background color if this tile is not part of an island
                if (x, y) not in self.colored_island_tiles:
                    if tile:
                        color = LIGHT_BLUE
                    elif self.selected_choice:
                        valid_positions = self.get_chunk_positions(self.selected_choice)
                        if (x, y) in valid_positions:
                            if self.hover_choice:
                                color = YELLOW  # Hover highlight
                            else:
                                color = LIGHT_GREEN  # Valid position
                    elif self.hover_choice:
                        # Show chunk preview for hovered choice
                        hover_positions = self.get_chunk_positions(self.hover_choice)
                        if (x, y) in hover_positions:
                            color = YELLOW  # Hover preview
                    
                    # Draw cell background only for non-island tiles
                    pygame.draw.rect(self.screen, color, (screen_x, screen_y, GRID_CELL_SIZE, GRID_CELL_SIZE))
                
                # Draw cell border for all tiles
                pygame.draw.rect(self.screen, BLACK, (screen_x, screen_y, GRID_CELL_SIZE, GRID_CELL_SIZE), 1)
                
                # Draw tile if present
                if tile:
                    icon = self.tile_icons.get(tile.choice.tile_type)
                    if icon:
                        self.screen.blit(icon, (screen_x, screen_y))
                    else:
                        text = self.font_small.render(tile.choice.tile_type[:3].upper(), True, BLACK)
                        text_rect = text.get_rect(center=(screen_x + GRID_CELL_SIZE//2, screen_y + GRID_CELL_SIZE//2))
                        self.screen.blit(text, text_rect)
                
                # Draw tile preview
                elif (self.hover_position == (x, y) and self.selected_choice):
                    icon = self.tile_icons.get(self.selected_choice.tile_type)
                    if icon:
                        # Create semi-transparent preview
                        preview_surface = icon.copy()
                        preview_surface.set_alpha(128)  # 50% transparency
                        self.screen.blit(preview_surface, (screen_x, screen_y))
                    else:
                        text = self.font_small.render(self.selected_choice.tile_type[:3].upper(), True, BLACK)
                        text_rect = text.get_rect(center=(screen_x + GRID_CELL_SIZE//2, screen_y + GRID_CELL_SIZE//2))
                        self.screen.blit(text, text_rect)
        
        # Draw border nodes (vertices) if in border turn
        if self.is_border_turn():
            for node in self.border_nodes:
                x, y = node  # x is column, y is row
                screen_x = GRID_OFFSET_X + x * GRID_CELL_SIZE
                screen_y = GRID_OFFSET_Y + y * GRID_CELL_SIZE
                
                # Check if this vertex is in the current path
                if node in self.border_drag_path:
                    # Highlight vertices in the current path
                    pygame.draw.circle(self.screen, ORANGE, (screen_x, screen_y), 6)
                else:
                    # Regular vertex nodes
                    pygame.draw.circle(self.screen, BLACK, (screen_x, screen_y), 3)
        
        # Draw existing border lines
        for border_line in self.save_state.border_lines:
            start_x, start_y = border_line.start_pos  # x is column, y is row
            end_x, end_y = border_line.end_pos
            
            start_screen_x = GRID_OFFSET_X + start_x * GRID_CELL_SIZE
            start_screen_y = GRID_OFFSET_Y + start_y * GRID_CELL_SIZE
            end_screen_x = GRID_OFFSET_X + end_x * GRID_CELL_SIZE
            end_screen_y = GRID_OFFSET_Y + end_y * GRID_CELL_SIZE
            
            pygame.draw.line(self.screen, DARK_GREEN, (start_screen_x, start_screen_y), (end_screen_x, end_screen_y), 3)
        
        # Draw current border lines being drawn
        for border_line in self.current_border_lines:
            start_x, start_y = border_line.start_pos  # x is column, y is row
            end_x, end_y = border_line.end_pos
            
            start_screen_x = GRID_OFFSET_X + start_x * GRID_CELL_SIZE
            start_screen_y = GRID_OFFSET_Y + start_y * GRID_CELL_SIZE
            end_screen_x = GRID_OFFSET_X + end_x * GRID_CELL_SIZE
            end_screen_y = GRID_OFFSET_Y + end_y * GRID_CELL_SIZE
            
            pygame.draw.line(self.screen, DARK_GREEN, (start_screen_x, start_screen_y), (end_screen_x, end_screen_y), 3)
        
        # Draw border preview
        if self.border_drag_active and len(self.border_drag_path) > 1:
            for i in range(len(self.border_drag_path) - 1):
                start_node = self.border_drag_path[i]
                end_node = self.border_drag_path[i + 1]
                
                start_x, start_y = start_node  # x is column, y is row
                end_x, end_y = end_node
                
                start_screen_x = GRID_OFFSET_X + start_x * GRID_CELL_SIZE
                start_screen_y = GRID_OFFSET_Y + start_y * GRID_CELL_SIZE
                end_screen_x = GRID_OFFSET_X + end_x * GRID_CELL_SIZE
                end_screen_y = GRID_OFFSET_Y + end_y * GRID_CELL_SIZE
                
                pygame.draw.line(self.screen, ORANGE, (start_screen_x, start_screen_y), (end_screen_x, end_screen_y), 3)
    
    def draw_choice_panel(self):
        """Draw the choice panel on the right"""
        panel_rect = pygame.Rect(CHOICE_PANEL_X, 20, CHOICE_PANEL_WIDTH, WINDOW_HEIGHT - 40)
        pygame.draw.rect(self.screen, LIGHT_GRAY, panel_rect)
        pygame.draw.rect(self.screen, BLACK, panel_rect, 2)
        
        available_choices = self.get_current_choices()
        
        if not available_choices:
            if self.is_border_turn():
                text = self.font_large.render("Border Drawing Phase!", True, BLACK)
                text_rect = text.get_rect(center=(CHOICE_PANEL_X + CHOICE_PANEL_WIDTH//2, 100))
                self.screen.blit(text, text_rect)
                
                text2 = self.font_medium.render("Drag on grid to draw borders", True, BLACK)
                text2_rect = text2.get_rect(center=(CHOICE_PANEL_X + CHOICE_PANEL_WIDTH//2, 150))
                self.screen.blit(text2, text2_rect)
                
                text3 = self.font_small.render("Draw enclosed areas to complete turn", True, BLACK)
                text3_rect = text3.get_rect(center=(CHOICE_PANEL_X + CHOICE_PANEL_WIDTH//2, 180))
                self.screen.blit(text3, text3_rect)
            else:
                text = self.font_medium.render("No choices available", True, BLACK)
                text_rect = text.get_rect(center=(CHOICE_PANEL_X + CHOICE_PANEL_WIDTH//2, 100))
                self.screen.blit(text, text_rect)
            return
        
        # Draw choices
        for i, choice in enumerate(available_choices[:2]):
            choice_y = 50 + i * 300
            self.draw_choice(choice, i + 1, choice_y)
    
    def draw_choice(self, choice: Choice, choice_num: int, y_offset: int):
        """Draw a single choice"""
        choice_rect = pygame.Rect(CHOICE_PANEL_X + 10, y_offset, CHOICE_PANEL_WIDTH - 20, 280)
        
        # Check if mouse is hovering over this choice
        mouse_in_choice = choice_rect.collidepoint(self.mouse_pos)
        
        # Choice background
        color = YELLOW if mouse_in_choice else WHITE
        if self.selected_choice == choice:
            color = LIGHT_GREEN
        pygame.draw.rect(self.screen, color, choice_rect)
        pygame.draw.rect(self.screen, BLACK, choice_rect, 2)
        
        # Choice title
        title = f"Choice {choice_num}: {choice.tile_type.title()}"
        title_text = self.font_medium.render(title, True, BLACK)
        self.screen.blit(title_text, (choice_rect.x + 10, choice_rect.y + 10))
        
        # Choice icon and chunk preview side by side with more spacing
        icon_x = choice_rect.x + 10
        icon_y = choice_rect.y + 50
        preview_x = icon_x + GRID_CELL_SIZE + 60  # Increased spacing from 40 to 60
        preview_y = icon_y
        
        # Draw choice icon
        icon = self.tile_icons.get(choice.tile_type)
        if icon:
            icon_rect = icon.get_rect()
            icon_rect.topleft = (icon_x, icon_y)
            self.screen.blit(icon, icon_rect)
        
        # Draw chunk preview next to icon
        self.draw_chunk_preview(choice, preview_x, preview_y)
        
        # Chunk info below
        chunk_info = f"Chunk: {choice.chunk_type.title()} #{choice.chunk_position}"
        chunk_text = self.font_small.render(chunk_info, True, BLACK)
        self.screen.blit(chunk_text, (choice_rect.x + 10, choice_rect.y + 200))
        
        # Selection indicator
        if self.selected_choice == choice:
            selected_text = self.font_small.render("✓ SELECTED", True, DARK_GREEN)
            self.screen.blit(selected_text, (choice_rect.x + 10, choice_rect.y + 220))
        
        # Handle choice hover
        if mouse_in_choice:
            self.hover_choice = choice
        elif self.hover_choice == choice:
            self.hover_choice = None
    
    def draw_chunk_preview(self, choice: Choice, x: int, y: int):
        """Draw a preview of the chunk for a choice"""
        preview_size = 120
        cell_size = preview_size // GRID_SIZE
        
        # Draw preview grid
        for y_pos in range(GRID_SIZE):  # Rows
            for x_pos in range(GRID_SIZE):  # Columns
                cell_x = x + x_pos * cell_size
                cell_y = y + y_pos * cell_size
                
                chunk_positions = self.get_chunk_positions(choice)
                if (x_pos, y_pos) in chunk_positions:  # (x, y) where x is column, y is row
                    color = LIGHT_GREEN
                else:
                    color = WHITE
                
                pygame.draw.rect(self.screen, color, (cell_x, cell_y, cell_size, cell_size))
                pygame.draw.rect(self.screen, BLACK, (cell_x, cell_y, cell_size, cell_size), 1)
    
    def draw_status_panel(self):
        """Draw the status panel on the left"""
        panel_rect = pygame.Rect(20, 20, 300, WINDOW_HEIGHT - 40)  # Increased width from 250 to 300
        pygame.draw.rect(self.screen, LIGHT_GRAY, panel_rect)
        pygame.draw.rect(self.screen, BLACK, panel_rect, 2)
        
        summary = self.game_runner.get_game_summary(self.save_state)
        
        # Game status
        if summary['game_ended']:
            status = f"Game Over! Final Score: {summary['current_points']}"
        else:
            status = f"Phase: {summary['phase'].title()}, Cycle: {summary['cycle']}"
        
        status_text = self.font_medium.render(status, True, BLACK)
        self.screen.blit(status_text, (30, 30))
        
        # Turn info
        turn_info = f"Turn: {summary['current_turn']}/{summary['total_turns']}"
        turn_text = self.font_small.render(turn_info, True, BLACK)
        self.screen.blit(turn_text, (30, 70))
        
        # Points - only show at end
        if summary['game_ended']:
            points_text = self.font_small.render(f"Final Points: {summary['current_points']}", True, BLACK)
            self.screen.blit(points_text, (30, 95))
        else:
            points_text = self.font_small.render("Points: Hidden until game end", True, BLACK)
            self.screen.blit(points_text, (30, 95))
        
        # Border info
        if self.is_border_turn():
            # Count lines: placed + in-progress drag
            in_progress = 0
            if self.border_drag_active and len(self.border_drag_path) > 1:
                in_progress = len(self.border_drag_path) - 1
            border_lines_drawn = len(self.current_border_lines) + in_progress
            border_info = f"Border lines: {border_lines_drawn}/{MAX_BORDER_LINES}"
        else:
            border_info = f"Border lines: 0/{MAX_BORDER_LINES}"
        border_text = self.font_small.render(border_info, True, BLACK)
        self.screen.blit(border_text, (30, 120))
        
        # Islands info
        islands_info = f"Islands formed: {summary['islands_formed']}"
        islands_text = self.font_small.render(islands_info, True, BLACK)
        self.screen.blit(islands_text, (30, 145))
        
        # Selected choice info
        if self.selected_choice:
            selected_text = self.font_small.render(f"Selected: {self.selected_choice.tile_type}", True, BLACK)
            self.screen.blit(selected_text, (30, 170))
            instruction_text = self.font_small.render("Click on valid position to place tile", True, BLACK)
            self.screen.blit(instruction_text, (30, 190))
        elif self.is_border_turn():
            instruction_text = self.font_small.render("Drag on grid to draw borders", True, BLACK)
            self.screen.blit(instruction_text, (30, 170))
            complete_text = self.font_small.render("Draw enclosed areas to complete", True, BLACK)
            self.screen.blit(complete_text, (30, 190))
    
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            elif event.type == pygame.MOUSEMOTION:
                self.mouse_pos = event.pos
                
                # Handle grid hover for tile preview
                grid_pos = self.get_grid_pos_from_mouse(event.pos)
                if grid_pos and self.selected_choice and not self.is_border_turn():
                    valid_positions = self.get_chunk_positions(self.selected_choice)
                    if grid_pos in valid_positions and not self.get_tile_at_position(grid_pos):
                        self.hover_position = grid_pos
                    else:
                        self.hover_position = None
                else:
                    self.hover_position = None
                
                # Update border drag path
                if self.border_drag_active:
                    vertex_pos = self.get_vertex_pos_from_mouse(event.pos)
                    if vertex_pos:
                        # Calculate how many lines would be drawn if we add this vertex
                        in_progress = len(self.border_drag_path) - 1 if len(self.border_drag_path) > 0 else 0
                        total_lines = len(self.current_border_lines) + in_progress
                        # Only allow adding if we don't exceed the limit
                        if total_lines < MAX_BORDER_LINES:
                            if len(self.border_drag_path) > 0:
                                last_vertex = self.border_drag_path[-1]
                                # Only allow horizontal or vertical moves
                                if (vertex_pos[0] == last_vertex[0] or vertex_pos[1] == last_vertex[1]) and \
                                   (abs(vertex_pos[0] - last_vertex[0]) <= 1 and abs(vertex_pos[1] - last_vertex[1]) <= 1):
                                    # Check if we're revisiting a vertex (for closing or undoing)
                                    if vertex_pos in self.border_drag_path:
                                        # Find the index of the revisited vertex
                                        revisit_index = self.border_drag_path.index(vertex_pos)
                                        # If we're revisiting the start vertex, close the border
                                        if revisit_index == 0 and len(self.border_drag_path) > 3:
                                            self.border_drag_path.append(vertex_pos)
                                            self.handle_border_release()
                                        # Otherwise, undo back to that vertex
                                        else:
                                            self.border_drag_path = self.border_drag_path[:revisit_index + 1]
                                    else:
                                        # Add new vertex if we haven't reached the limit
                                        self.border_drag_path.append(vertex_pos)
                        else:
                            # Exceeded the limit: stop the drag and reset
                            print("Border limit reached! Drag cancelled.")
                            self.border_drag_active = False
                            self.border_drag_path = []
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self.handle_mouse_click(event.pos)
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:  # Left click release
                    self.handle_mouse_release(event.pos)
        
        return True
    
    def handle_mouse_click(self, pos: Tuple[int, int]):
        """Handle mouse click events"""
        # Check if clicking on choice panel
        if pos[0] > CHOICE_PANEL_X:
            available_choices = self.get_current_choices()
            for i, choice in enumerate(available_choices[:2]):
                choice_rect = pygame.Rect(CHOICE_PANEL_X + 10, 50 + i * 300, CHOICE_PANEL_WIDTH - 20, 280)
                if choice_rect.collidepoint(pos):
                    self.select_choice(choice)
                    return
        
        # Check if clicking on grid
        if self.is_border_turn():
            vertex_pos = self.get_vertex_pos_from_mouse(pos)
            if vertex_pos:
                self.handle_border_click(vertex_pos)
        else:
            grid_pos = self.get_grid_pos_from_mouse(pos)
            if grid_pos and self.selected_choice:
                self.handle_tile_placement_click(grid_pos)
    
    def handle_mouse_release(self, pos: Tuple[int, int]):
        """Handle mouse release events"""
        if self.border_drag_active:
            self.handle_border_release()
    
    def handle_tile_placement_click(self, grid_pos: Tuple[int, int]):
        """Handle tile placement click"""
        if not self.selected_choice:
            return
        
        # Check if position is valid
        valid_positions = self.get_chunk_positions(self.selected_choice)
        if grid_pos in valid_positions and not self.get_tile_at_position(grid_pos):
            self.place_tile_at_position(grid_pos)
    
    def handle_border_click(self, vertex_pos: Tuple[int, int]):
        """Handle border drawing click"""
        if not self.is_border_turn():
            return
        
        self.border_drag_start = vertex_pos
        self.border_drag_path = [vertex_pos]
        self.border_drag_active = True
    
    def handle_border_release(self):
        """Handle border drawing release"""
        if not self.border_drag_active:
            return
        
        self.border_drag_active = False
        
        # Check if the path is valid and forms an enclosed area
        if self.is_valid_border_path(self.border_drag_path) and self.is_enclosed_path(self.border_drag_path):
            border_lines = self.create_border_lines_from_path(self.border_drag_path)
            
            if len(self.current_border_lines) + len(self.border_drag_path) <= MAX_BORDER_LINES:
                self.current_border_lines.extend(border_lines)
                print("Border created successfully!")
                
                # Auto-complete the turn when a border is drawn
                self.complete_border_turn()
            else:
                print("Border limit reached!")
        else:
            print("Invalid border path or not enclosed")
        
        self.border_drag_path = []
    
    def border_lines_to_tile_positions(self, border_lines: List[BorderLine]) -> List[Tuple[int, int]]:
        """Convert border lines to enclosed tile positions using ray casting"""
        if not border_lines:
            return []
        
        # Build a list of line segments
        segments = []
        for line in border_lines:
            segments.append((line.start_pos, line.end_pos))
        
        enclosed_tiles = []
        for y in range(GRID_SIZE):  # Rows
            for x in range(GRID_SIZE):  # Columns
                # Cast a vertical ray upward from the center of the tile
                ray_x = x + 0.5
                ray_y = y + 0.5
                crossings = 0
                for (start, end) in segments:
                    (x1, y1), (x2, y2) = start, end  # Already in (x, y) format
                    # Only consider segments that cross the ray vertically
                    if min(y1, y2) < ray_y <= max(y1, y2):
                        # Compute the x coordinate where the segment crosses ray_y
                        if y2 != y1:
                            x_cross = x1 + (x2 - x1) * (ray_y - y1) / (y2 - y1)
                            if x_cross > ray_x:
                                crossings += 1
                if crossings % 2 == 1:
                    enclosed_tiles.append((x, y))  # (x, y) where x is column, y is row
        
        return enclosed_tiles

    def complete_border_turn(self):
        """Complete the border drawing turn"""
        if not self.is_border_turn():
            return
        
        try:
            # Create dummy choices for border turn
            dummy_choice1 = Choice("houses", "cluster", 1)
            dummy_choice2 = Choice("ships", "cluster", 2)
            print(f"Completing border turn. Current turn: {self.save_state.current_turn}")
            print(f"Border lines to add: {len(self.current_border_lines)}")
            print(f"Border lines sent: {[str(line) for line in self.current_border_lines]}")
            
            # Convert border lines to tile positions
            border_tiles = self.border_lines_to_tile_positions(self.current_border_lines)
            print(f"Converted to {len(border_tiles)} border tiles: {border_tiles}")
            
            prev_island_positions = set()
            if hasattr(self, 'save_state') and hasattr(self.save_state, 'islands'):
                for island in self.save_state.islands:
                    prev_island_positions.update(island.enclosed_positions)
            
            self.save_state = self.game_runner.make_turn(
                self.save_state,
                dummy_choice1,
                dummy_choice2,
                (0, 0),  # Dummy position
                border_tiles  # Send tile positions instead of border lines
            )
            
            # Find new island positions (those not present before this border turn)
            new_island_positions = set()
            for island in self.save_state.islands:
                new_island_positions.update(island.enclosed_positions)
            just_created = new_island_positions - prev_island_positions
            print(f"prev_island_positions: {prev_island_positions}")
            print(f"new_island_positions: {new_island_positions}")
            print(f"just_created: {just_created}")
            self.colored_island_tiles.update(just_created)
            
            # Reset border drawing state
            self.current_border_lines = []
            self.clear_current_choices()
            print(f"Border turn completed! New turn: {self.save_state.current_turn}")
        except Exception as e:
            print(f"Error completing border turn: {e}")
            import traceback
            traceback.print_exc()
    
    def get_island_tile_positions(self) -> set:
        """Return a set of all (x, y) positions that are enclosed by border lines (i.e., on any island)."""
        island_positions = set()
        for island in self.save_state.islands:
            island_positions.update(island.enclosed_positions)
        return island_positions
    
    def run(self):
        """Main game loop"""
        running = True
        while running:
            try:
                running = self.handle_events()
                
                # Draw everything
                self.screen.fill(WHITE)
                self.draw_grid()
                self.draw_choice_panel()
                self.draw_status_panel()
                
                pygame.display.flip()
                self.clock.tick(60)
                
            except Exception as e:
                print(f"Error in game loop: {e}")
                import traceback
                traceback.print_exc()
                running = False
        
        pygame.quit()
        sys.exit()

def main():
    game = GameUI()
    game.run()

if __name__ == "__main__":
    main() 