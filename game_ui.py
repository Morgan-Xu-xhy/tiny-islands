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
            row = (y - GRID_OFFSET_Y) // GRID_CELL_SIZE
            col = (x - GRID_OFFSET_X) // GRID_CELL_SIZE
            return (row, col)
        return None
    
    def get_vertex_pos_from_mouse(self, mouse_pos: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        """Convert mouse position to vertex position (tile corner)"""
        x, y = mouse_pos
        if (GRID_OFFSET_X <= x < GRID_OFFSET_X + (GRID_SIZE + 1) * GRID_CELL_SIZE and
            GRID_OFFSET_Y <= y < GRID_OFFSET_Y + (GRID_SIZE + 1) * GRID_CELL_SIZE):
            # Calculate which vertex the mouse is closest to
            vertex_row = round((y - GRID_OFFSET_Y) / GRID_CELL_SIZE)
            vertex_col = round((x - GRID_OFFSET_X) / GRID_CELL_SIZE)
            
            # Clamp to valid range
            vertex_row = max(0, min(GRID_SIZE, vertex_row))
            vertex_col = max(0, min(GRID_SIZE, vertex_col))
            
            return (vertex_row, vertex_col)
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
            cluster_row = ((chunk_position - 1) // 3) * 3
            cluster_col = ((chunk_position - 1) % 3) * 3
            for row in range(cluster_row, cluster_row + 3):
                for col in range(cluster_col, cluster_col + 3):
                    positions.append((row, col))
        
        elif chunk_type == "horizontal":
            # Horizontal rows, numbered 1-9 from top to bottom
            row = chunk_position - 1
            for col in range(GRID_SIZE):
                positions.append((row, col))
        
        elif chunk_type == "vertical":
            # Vertical columns, numbered 1-9 from left to right
            col = chunk_position - 1
            for row in range(GRID_SIZE):
                positions.append((row, col))
        
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
        # Draw grid cells
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                x = GRID_OFFSET_X + col * GRID_CELL_SIZE
                y = GRID_OFFSET_Y + row * GRID_CELL_SIZE
                
                # Determine cell color
                color = WHITE
                tile = self.get_tile_at_position((row, col))
                
                if tile:
                    color = LIGHT_BLUE
                elif self.selected_choice:
                    valid_positions = self.get_chunk_positions(self.selected_choice)
                    if (row, col) in valid_positions:
                        if self.hover_choice:
                            color = YELLOW  # Hover highlight
                        else:
                            color = LIGHT_GREEN  # Valid position
                elif self.hover_choice:
                    # Show chunk preview for hovered choice
                    hover_positions = self.get_chunk_positions(self.hover_choice)
                    if (row, col) in hover_positions:
                        color = YELLOW  # Hover preview
                
                # Draw cell background
                pygame.draw.rect(self.screen, color, (x, y, GRID_CELL_SIZE, GRID_CELL_SIZE))
                pygame.draw.rect(self.screen, BLACK, (x, y, GRID_CELL_SIZE, GRID_CELL_SIZE), 1)
                
                # Draw tile if present
                if tile:
                    icon = self.tile_icons.get(tile.choice.tile_type)
                    if icon:
                        self.screen.blit(icon, (x, y))
                    else:
                        text = self.font_small.render(tile.choice.tile_type[:3].upper(), True, BLACK)
                        text_rect = text.get_rect(center=(x + GRID_CELL_SIZE//2, y + GRID_CELL_SIZE//2))
                        self.screen.blit(text, text_rect)
                
                # Draw tile preview
                elif (self.hover_position == (row, col) and self.selected_choice):
                    icon = self.tile_icons.get(self.selected_choice.tile_type)
                    if icon:
                        # Create semi-transparent preview
                        preview_surface = icon.copy()
                        preview_surface.set_alpha(128)  # 50% transparency
                        self.screen.blit(preview_surface, (x, y))
                    else:
                        text = self.font_small.render(self.selected_choice.tile_type[:3].upper(), True, BLACK)
                        text_rect = text.get_rect(center=(x + GRID_CELL_SIZE//2, y + GRID_CELL_SIZE//2))
                        self.screen.blit(text, text_rect)
        
        # Draw border nodes (vertices) if in border turn
        if self.is_border_turn():
            for node in self.border_nodes:
                row, col = node
                x = GRID_OFFSET_X + col * GRID_CELL_SIZE
                y = GRID_OFFSET_Y + row * GRID_CELL_SIZE
                
                # Check if this vertex is in the current path
                if node in self.border_drag_path:
                    # Highlight vertices in the current path
                    pygame.draw.circle(self.screen, ORANGE, (x, y), 6)
                else:
                    # Regular vertex nodes
                    pygame.draw.circle(self.screen, BLACK, (x, y), 3)
        
        # Draw existing border lines
        for border_line in self.save_state.border_lines:
            start_row, start_col = border_line.start_pos
            end_row, end_col = border_line.end_pos
            
            start_x = GRID_OFFSET_X + start_col * GRID_CELL_SIZE
            start_y = GRID_OFFSET_Y + start_row * GRID_CELL_SIZE
            end_x = GRID_OFFSET_X + end_col * GRID_CELL_SIZE
            end_y = GRID_OFFSET_Y + end_row * GRID_CELL_SIZE
            
            pygame.draw.line(self.screen, DARK_GREEN, (start_x, start_y), (end_x, end_y), 3)
        
        # Draw current border lines being drawn
        for border_line in self.current_border_lines:
            start_row, start_col = border_line.start_pos
            end_row, end_col = border_line.end_pos
            
            start_x = GRID_OFFSET_X + start_col * GRID_CELL_SIZE
            start_y = GRID_OFFSET_Y + start_row * GRID_CELL_SIZE
            end_x = GRID_OFFSET_X + end_col * GRID_CELL_SIZE
            end_y = GRID_OFFSET_Y + end_row * GRID_CELL_SIZE
            
            pygame.draw.line(self.screen, DARK_GREEN, (start_x, start_y), (end_x, end_y), 3)
        
        # Draw border preview
        if self.border_drag_active and len(self.border_drag_path) > 1:
            for i in range(len(self.border_drag_path) - 1):
                start_node = self.border_drag_path[i]
                end_node = self.border_drag_path[i + 1]
                
                start_row, start_col = start_node
                end_row, end_col = end_node
                
                start_x = GRID_OFFSET_X + start_col * GRID_CELL_SIZE
                start_y = GRID_OFFSET_Y + start_row * GRID_CELL_SIZE
                end_x = GRID_OFFSET_X + end_col * GRID_CELL_SIZE
                end_y = GRID_OFFSET_Y + end_row * GRID_CELL_SIZE
                
                pygame.draw.line(self.screen, ORANGE, (start_x, start_y), (end_x, end_y), 3)
    
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
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                cell_x = x + col * cell_size
                cell_y = y + row * cell_size
                
                chunk_positions = self.get_chunk_positions(choice)
                if (row, col) in chunk_positions:
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
        border_info = f"Border lines: {summary['border_lines_drawn']}/{MAX_BORDER_LINES}"
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
                        # Check if we can add this vertex
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
                                    if len(self.save_state.border_lines) + len(self.current_border_lines) + len(self.border_drag_path) < MAX_BORDER_LINES:
                                        self.border_drag_path.append(vertex_pos)
                        else:
                            self.border_drag_path.append(vertex_pos)
            
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
            
            if len(self.save_state.border_lines) + len(self.current_border_lines) + len(border_lines) <= MAX_BORDER_LINES:
                self.current_border_lines.extend(border_lines)
                print("Border created successfully!")
                
                # Auto-complete the turn when a border is drawn
                self.complete_border_turn()
            else:
                print("Border limit reached!")
        else:
            print("Invalid border path or not enclosed")
        
        self.border_drag_path = []
    
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
            
            self.save_state = self.game_runner.make_turn(
                self.save_state,
                dummy_choice1,
                dummy_choice2,
                (0, 0),  # Dummy position
                self.current_border_lines
            )
            
            # Reset border drawing state
            self.current_border_lines = []
            self.clear_current_choices()
            print(f"Border turn completed! New turn: {self.save_state.current_turn}")
            
        except Exception as e:
            print(f"Error completing border turn: {e}")
            import traceback
            traceback.print_exc()
    
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