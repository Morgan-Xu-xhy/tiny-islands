#!/usr/bin/env python3

from game import GameRunner, Choice

def test_border_validation():
    """Test the border tile validation functionality"""
    game_runner = GameRunner()
    save_state = game_runner.create_new_game()
    
    print("=== Testing Border Tile Validation ===")
    
    # Test 1: Valid enclosed area (using new coordinate system: x=column, y=row)
    valid_tiles = [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2), (1, 2), (0, 2), (0, 1)]  # Clockwise from top-left
    print(f"Test 1 - Valid enclosed area: {valid_tiles}")
    is_valid = game_runner._validate_border_tiles(valid_tiles)
    print(f"Result: {is_valid}")
    border_length = game_runner._calculate_border_length(valid_tiles)
    print(f"Border length: {border_length}")
    print()
    
    # Test 2: Invalid - not connected
    invalid_tiles = [(0, 0), (1, 0), (2, 2), (3, 2)]  # Not connected
    print(f"Test 2 - Invalid (not connected): {invalid_tiles}")
    is_valid = game_runner._validate_border_tiles(invalid_tiles)
    print(f"Result: {is_valid}")
    print()
    
    # Test 3: Invalid - has hole
    invalid_tiles_with_hole = [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2), (1, 2), (0, 2), (0, 1), (1, 1)]  # Hole in middle
    print(f"Test 3 - Invalid (has hole): {invalid_tiles_with_hole}")
    is_valid = game_runner._validate_border_tiles(invalid_tiles_with_hole)
    print(f"Result: {is_valid}")
    print()
    
    # Test 4: Border turn with valid tiles
    print("Test 4 - Making a border turn with valid tiles")
    try:
        new_save_state = game_runner.make_turn(
            save_state,
            Choice("houses", "cluster", 1),
            Choice("ships", "cluster", 2),
            (0, 0),
            valid_tiles
        )
        print("Success! Border turn completed.")
        print(f"New turn: {new_save_state.current_turn}")
        print(f"Islands formed: {len(new_save_state.islands)}")
        if new_save_state.islands:
            island = new_save_state.islands[0]
            print(f"Island tiles: {island.enclosed_positions}")
            print(f"Border lines: {len(island.border_lines)}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== Test completed ===")

if __name__ == "__main__":
    test_border_validation() 