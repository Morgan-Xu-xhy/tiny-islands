# Tiny Islands Game Implementation

## Table of Contents
1. [About Tiny Islands (2019)](#about-tiny-islands-2019)
2. [Project Goals](#project-goals)
3. [Current Implementation Status](#current-implementation-status)
4. [Game Structure](#game-structure)
5. [Getting Started](#getting-started)
6. [Future Development](#future-development)
7. [Contributing](#contributing)
8. [License](#license)

## About Tiny Islands (2019)

Tiny Islands is a fun tabletop-like grid-based game that challenges players to explore synergies between different tile types in a terraforming journey. Players strategically place various tiles (houses, churches, forests, mountains, ships, waves, and beaches) on a 9x9 grid, then draw borders to create islands and lakes. The goal is to maximize points by placing tiles in optimal locations that satisfy their unique scoring rules and terrain preferences.

## Project Goals

This project aims to replicate the Tiny Islands game digitally and eventually use machine learning to find optimal solutions. The long-term vision is to:

- **Statistical Modeling**: Analyze game patterns and identify high-scoring strategies
- **Neural Networks**: Train AI models to predict optimal tile placements
- **Reinforcement Learning**: Develop agents that can learn and improve their gameplay through experience
- **Strategy Insights**: Provide gamers with data-driven recommendations for optimal play

## Current Implementation Status

### Completed Features

#### Game Engine (MVC Architecture)
- **Game Controller** (`game.py`): Complete MVC implementation with proper separation of concerns
- **Save State System**: Full game state persistence with JSON serialization
- **Turn Management**: 30-turn game structure (9 choice turns + 1 border turn, repeated 3 times)
- **Choice Generation**: Random tile and chunk selection system
- **Border Drawing**: Complete border line management with 24-line limit

#### Data Structures
- **Tile Types**: Houses, Waves, Ships, Forest, Mountain, Churches, Beach
- **Chunk Types**: Cluster (3x3), Horizontal (rows), Vertical (columns)
- **Border System**: Island and lake detection with flood-fill algorithm
- **Turn History**: Complete tracking of all game decisions

#### User Interface (Pygame)
- **Main Game Grid**: 9x9 interactive grid with visual tile placement
- **Choice Panel**: Side-by-side tile and chunk preview display
- **Status Panel**: Real-time game information and turn tracking
- **Border Drawing**: Vertex-based border creation with undo/redo functionality
- **Visual Feedback**: Hover effects, chunk previews, and selection indicators

#### Game Mechanics
- **Tile Placement**: Valid chunk position enforcement
- **Border Drawing**: Grid-aligned line drawing with enclosed area detection
- **Turn Progression**: Automatic advancement between choice and border phases
- **Point Calculation**: Complete scoring system (hidden until game end)
- **Terrain Penalties**: 5-point penalties for features in wrong locations

### Scoring System Implementation

All tile-specific scoring rules are implemented:

- **Ships**: 1pt per square separation from nearest boat/island
- **Waves**: 2pts for each wave following rules (no same row/column, no nearby waves)
- **Beach**: 1pt per side touching an island
- **Houses**: 1pt per unique nearby feature (excluding other houses)
- **Churches**: 2pts per nearby house, 1pt per additional house on same island, 0 if another church on island
- **Forest**: 2pts per forest in group minus 2pts
- **Mountain**: 2pts per nearby forest

### Island Detection System

- **Flood-Fill Algorithm**: Detects enclosed areas from border lines
- **Island vs Lake**: Distinguishes between islands and lakes (enclosed areas within islands)
- **Terrain Analysis**: Determines which tiles should be on land vs sea
- **Penalty System**: 5-point penalties for misplaced features

### User Experience Features

- **Responsive UI**: Larger text, better spacing, no overlap issues
- **Visual Feedback**: 
  - Hover effects on choices and grid positions
  - Chunk previews on main grid when hovering over choices
  - Border vertex highlighting during drawing
  - Tile placement previews
- **Border Drawing**: 
  - Vertex-based drawing (tile corners)
  - Undo functionality by revisiting vertices
  - Automatic border closing when returning to start
  - Grid-aligned only (no diagonal lines)
- **Game Flow**: 
  - Automatic turn completion after border drawing
  - Proper choice generation for each turn
  - Points hidden until game end

### Technical Implementation

#### Architecture
- **MVC Pattern**: Clean separation between game logic and UI
- **Data Classes**: Type-safe data structures with serialization
- **Event-Driven UI**: Responsive pygame interface
- **State Management**: Proper save/load functionality

#### Code Quality
- **Type Hints**: Full type annotation throughout
- **Error Handling**: Comprehensive exception handling with debugging
- **Modular Design**: Well-organized, maintainable code structure
- **Documentation**: Detailed docstrings and comments

## Game Structure

### Turn Sequence
1. **Turns 1-9**: Choice turns (place tiles)
2. **Turn 10**: Border drawing turn
3. **Turns 11-19**: Choice turns (place tiles)
4. **Turn 20**: Border drawing turn
5. **Turns 21-29**: Choice turns (place tiles)
6. **Turn 30**: Final border drawing turn

### Scoring Rules
- Points are calculated only at game end
- Terrain penalties apply for misplaced features
- Each tile type has specific scoring conditions
- Border lines create islands/lakes that affect scoring

## Getting Started

### Prerequisites
- Python 3.7+
- Pygame

### Installation
```bash
git clone https://github.com/Morgan-Xu-xhy/tiny-islands
cd tiny-islands
pip install pygame
```

### Running the Game
```bash
python game_ui.py
```

### Game Controls
- **Mouse**: Click to select choices and place tiles
- **Border Drawing**: Click and drag on grid vertices to draw borders
- **Undo**: Revisit a vertex to undo border drawing
- **Close Border**: Return to starting vertex to complete border

## Future Development

### Phase 1: Game Logic and UI Improvements
- [ ] Revisiting and polishing scoring logic
- [ ] Quality of life features for frontend: marking islands to use a different color than the default non-land color (#E9E9E9) after each border is drawn
- [ ] Remove background from current screenshotted icon assets
- [ ] Record scaled number of live sessions on itch.io and extract probability data, guess is that tiles and chunks might not appear completely randomly. Could be a false random or scaled for some common tiles

### Phase 2: Statistical Modeling
- [ ] Game pattern analysis
- [ ] High-scoring strategy identification
- [ ] Probability modeling of optimal moves
- [ ] Statistical recommendation system

### Phase 3: Machine Learning
- [ ] Neural network for move prediction
- [ ] Reinforcement learning agent training
- [ ] Strategy optimization algorithms
- [ ] AI vs AI gameplay analysis

### Phase 4: Strategy Insights
- [ ] Player recommendation system
- [ ] Optimal strategy guides
- [ ] Performance analytics dashboard
- [ ] Community strategy sharing

## Contributing

This project welcomes contributions! Areas for improvement include:
- Enhanced AI algorithms
- Additional game analysis tools
- UI/UX improvements
- Performance optimizations
- Documentation and testing

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.