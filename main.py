import os
import platform
import subprocess
import sys
import pygame
import noise
import random
from music_generator import MusicGenerator
from sound_effects import SoundEffects
from threading import Thread, Event
import math
import atexit
import signal

# Initialize Pygame
pygame.init()

# Keep track of whether we're shutting down
_is_shutting_down = False

def _quit_pygame():
    """Quit pygame after threads have finished"""
    global _is_shutting_down
    _is_shutting_down = True
    try:
        pygame.quit()
    except:
        pass

# Register the cleanup function
atexit.register(_quit_pygame)

def signal_handler(sig, frame):
    """Handle system signals gracefully"""
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def signal_loading_complete():
    """Signal that the game has finished loading"""
    if platform.system() == 'Darwin':
        # Get the .app bundle MacOS directory
        if getattr(sys, 'frozen', False):
            # Running as bundled app
            bundle_dir = os.path.dirname(sys.executable)
            ready_path = os.path.join(bundle_dir, '.ready')
        else:
            # Running in development
            ready_path = '.ready'
        
        # Create the ready file
        try:
            with open(ready_path, 'w') as f:
                f.write('ready')
        except Exception as e:
            print(f"Failed to create ready file: {e}")

@atexit.register
def cleanup_pygame():
    """Clean up Pygame resources at exit"""
    try:
        if pygame.mixer.get_init():
            pygame.mixer.stop()
            pygame.mixer.quit()
    except:
        pass
    try:
        pygame.display.quit()
    except:
        pass
    try:
        pygame.quit()
    except:
        pass

# Constants
WINDOW_SIZE = 800
CELL_SIZE = 40
GRID_SIZE = WINDOW_SIZE // CELL_SIZE
PLAYER_SIZE = CELL_SIZE - 8
FPS = 60
GRAVITY = 0.15
INITIAL_BLOCKS = 30

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 100, 100)
GREEN = (100, 255, 150)
BLUE = (100, 150, 255)
PORTAL_COLORS = [(100, 150, 255), (150, 200, 255)]
GREY = (128, 128, 128)
GRID_COLOR = (50, 50, 50)

# New color constants for effects
PLAYER_GLOW = (255, 150, 150, 100)
ENDPOINT_GLOW = (150, 200, 255, 100)
BLOCK_COLOR = (180, 180, 180)

# New constants for the direction indicator
INDICATOR_LENGTH = CELL_SIZE * 0.6
INDICATOR_WIDTH = 3
INDICATOR_COLOR = (255, 200, 200, 160)
INDICATOR_HEAD_SIZE = 6

# Game over text colors
GAME_OVER_COLOR = (255, 50, 50)
RESTART_TEXT_COLOR = (200, 200, 200)

# Danger indicator colors
DANGER_COLOR = (255, 50, 50, 80)
DANGER_BORDER = (255, 50, 50)
INVALID_MOVE_COLOR = (255, 100, 100, 40)

# Movement lock indicator
MOVEMENT_LOCK_COLOR = (255, 200, 50, 100)
MOVEMENT_LOCK_BORDER = (255, 200, 50)

# Game over states
DEATH_CRUSHED = "You've been smooshed!"
DEATH_TRAPPED = "You're trapped!"

# Menu states
MENU_INTRO = "intro"
MENU_GAME = "game"
MENU_PAUSE = "pause"
MENU_OPTIONS = "options"
MENU_KEYBIND = "keybind"
MENU_TUTORIAL = "tutorial"

# Menu colors
MENU_BG = (0, 0, 0, 180)
MENU_TEXT = (255, 255, 255)
MENU_HIGHLIGHT = (255, 200, 100)
MENU_SELECTED = (255, 150, 50)
MENU_TITLE = (100, 200, 255)
MENU_DESCRIPTION = (200, 255, 200)
MENU_SECTION_TITLE = (255, 180, 100)

# Tutorial section spacing
TUTORIAL_SECTION_SPACING = 120
TUTORIAL_TEXT_SPACING = 30

# Default keybindings
DEFAULT_KEYS = {
    "up": [pygame.K_UP, pygame.K_w],
    "down": [pygame.K_DOWN, pygame.K_s],
    "left": [pygame.K_LEFT, pygame.K_a],
    "right": [pygame.K_RIGHT, pygame.K_d],
    "contrast": pygame.K_SPACE,
    "restart": pygame.K_r,
    "pause": pygame.K_ESCAPE
}

class FallingBlock:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.y_velocity = 0
        self.falling = True
        self.size = PLAYER_SIZE
        # Add a small random initial delay to stagger the falling
        self.fall_delay = random.randint(0, 30)

    def should_start_falling(self):
        if self.fall_delay > 0:
            self.fall_delay -= 1
            return False
        return True

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
        # Create surfaces for transitions
        self.transition_surface = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
        self.level_transition_surface = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE))
        pygame.display.set_caption("The Inverse Path")
        self.clock = pygame.time.Clock()
        
        # Menu state
        self.menu_state = MENU_INTRO
        self.previous_menu = None
        self.selected_menu_item = 0
        self.keybindings = DEFAULT_KEYS.copy()
        self.waiting_for_key = None
        
        # Volume settings (initialize before sound systems)
        self.sfx_volume = 1.0
        self.music_volume = 0.5
        self.sfx_muted = False
        self.music_muted = False
        
        # Initialize sound systems
        self.sound_effects = SoundEffects()
        self.music_gen = MusicGenerator()
        self.music_thread = None
        self.music_stop_event = Event()
        
        # Menu fonts
        self.title_font = pygame.font.Font(None, 84)
        self.menu_font = pygame.font.Font(None, 48)
        self.submenu_font = pygame.font.Font(None, 36)
        
        # Game fonts
        self.player_font = pygame.font.Font(None, CELL_SIZE)
        self.game_over_font = pygame.font.Font(None, 72)
        self.restart_font = pygame.font.Font(None, 36)
        self.level_announcement_font = pygame.font.Font(None, 72)
        self.level_announcement_small_font = pygame.font.Font(None, 36)
        
        # Game state
        self.level = 1
        self.colors_inverted = False
        self.falling_blocks = []
        self.movement_delay = 0
        self.movement_cooldown = 10
        
        # Block count scaling
        self.BASE_BLOCKS = 7  # Starting number of blocks for level 1
        self.MAX_BLOCKS = 40   # Maximum number of blocks at higher levels
        self.BLOCKS_PER_LEVEL = 1  # How many blocks to add per level
        
        # Transition effect variables
        self.transition_alpha = 0
        self.transition_speed = 8
        self.is_transitioning = False
        
        # Level transition variables
        self.level_transition_alpha = 0
        self.level_transition_speed = 4
        self.is_level_transitioning = False
        self.level_transition_state = 'none'
        self.transition_hold_timer = 0
        self.transition_hold_duration = 30
        self.is_first_level = True
        self.level_text_alpha = 0
        self.next_level = 1
        
        # Animation variables
        self.animation_tick = 0
        
        # Spawn animation variables
        self.spawn_animation_duration = 60
        self.spawn_animation_timer = 0
        self.spawn_rings = []
        
        # Gameplay constants
        self.MIN_START_DISTANCE = GRID_SIZE // 2
        
        # Game state variables
        self.game_over = False
        self.game_over_alpha = 0
        self.game_over_reason = ""
        self.death_animation_timer = 0
        self.death_animation_duration = 60
        self.death_particles = []
        
        # Preview state for contrast switch
        self.showing_contrast_preview = False
        self.preview_alpha = 0
        self.preview_fade_speed = 8
        
        # Movement lock state
        self.movement_locked = False
        
        # Start background music
        self.start_background_music()
        
        self.reset_game()
        
        # Signal that loading is complete
        signal_loading_complete()

    def start_background_music(self):
        """Start playing music in a background thread"""
        if self.music_thread is not None:
            self.music_stop_event.set()
            self.music_thread.join()
            self.music_stop_event.clear()
        
        # Set initial volume
        self.music_gen.set_volume(self.music_volume)
        self.music_gen.set_muted(self.music_muted)
        
        def music_loop():
            while not self.music_stop_event.is_set():
                self.music_gen.play_song()
        
        self.music_thread = Thread(target=music_loop, daemon=True)
        self.music_thread.start()

    def find_safe_position(self):
        """Find a safe position for the player that won't result in immediate death"""
        # Try all positions on the grid
        for x in range(GRID_SIZE):
            for y in range(GRID_SIZE):
                if self.grid[x][y] != self.colors_inverted and self.is_position_safe_from_blocks(x, y):
                    # Check if this position has at least one valid move
                    has_valid_move = False
                    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        new_x = x + dx
                        new_y = y + dy
                        if self.will_position_be_valid(new_x, new_y, self.endpoint):
                            has_valid_move = True
                            break
                    
                    if has_valid_move:
                        return [x, y]
        return None

    def reset_game(self):
        attempts = 0
        max_attempts = 10
        valid_layout = False
        
        while not valid_layout and attempts < max_attempts:
            # Generate new level
            self.generate_grid()
            
            # Try to find valid positions
            player_pos, endpoint_pos = self.find_valid_positions(self.MIN_START_DISTANCE)
            
            if player_pos is not None and endpoint_pos is not None:
                self.player_pos = list(player_pos)
                self.endpoint = endpoint_pos
                
                # Create falling blocks and verify they don't create an impossible situation
                self.create_falling_blocks()
                
                # Final verification that the position is playable
                if not self.check_player_trapped():
                    valid_layout = True
                else:
                    # If player is trapped immediately, try to find a new safe position
                    new_pos = self.find_safe_position()
                    if new_pos is not None:
                        self.player_pos = new_pos
                        valid_layout = True
            
            attempts += 1
        
        if not valid_layout:
            # If we couldn't find valid positions after max attempts,
            # regenerate the grid with more walkable spaces and fewer blocks
            self.generate_grid(make_easier=True)
            # Try one last time with relaxed constraints
            player_pos, endpoint_pos = self.find_valid_positions(self.MIN_START_DISTANCE // 2)
            if player_pos is not None and endpoint_pos is not None:
                self.player_pos = list(player_pos)
                self.endpoint = endpoint_pos
                # Create falling blocks with reduced count and higher initial positions
                self.falling_blocks = []
                reduced_blocks = INITIAL_BLOCKS // 3
                for _ in range(reduced_blocks):
                    x = random.randint(0, GRID_SIZE-1)
                    y = random.uniform(0, 2)  # Start blocks higher up
                    block = FallingBlock(x, y)
                    block.fall_delay = random.randint(60, 120)  # Longer delays
                    self.falling_blocks.append(block)
            else:
                # Last resort: just place them randomly with minimal blocks
                self.place_player_old()
                self.place_endpoint_old()
                self.falling_blocks = []
        
        # Only start spawn animation immediately for the first level
        if self.is_first_level:
            self.start_spawn_animation()
            self.is_first_level = False
        
        # If this is level 1, start with a fade-in transition
        if self.level == 1:
            self.is_level_transitioning = True
            self.level_transition_state = 'fadein'
            self.level_transition_alpha = 255
            self.transition_hold_timer = self.transition_hold_duration
        
        # Start with movement locked until initial blocks settle
        self.movement_locked = True

    def start_spawn_animation(self):
        """Initialize the spawn animation"""
        self.spawn_animation_timer = self.spawn_animation_duration
        self.spawn_rings = []
        # Create 3 rings that will expand outward
        for i in range(3):
            self.spawn_rings.append({
                'delay': i * 15,
                'radius': 0,
                'alpha': 255
            })

    def draw_spawn_animation(self, surface):
        """Draw the spawn animation effect"""
        if self.spawn_animation_timer > 0:
            player_center_x = self.player_pos[0] * CELL_SIZE + CELL_SIZE // 2
            player_center_y = self.player_pos[1] * CELL_SIZE + CELL_SIZE // 2
            
            # Create a surface for the rings
            ring_surface = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
            
            # Update and draw each ring
            for ring in self.spawn_rings:
                if self.spawn_animation_timer < ring['delay']:
                    continue
                
                # Calculate ring properties
                time_since_start = self.spawn_animation_duration - self.spawn_animation_timer + ring['delay']
                ring['radius'] = int(time_since_start * 1.5)
                ring['alpha'] = max(0, 255 - (time_since_start * 4))
                
                # Draw the ring
                if ring['alpha'] > 0:
                    ring_color = (*RED[:3], ring['alpha'])
                    pygame.draw.circle(ring_surface, ring_color,
                                    (player_center_x, player_center_y),
                                    ring['radius'], 2)
            
            # Draw highlight in player's cell
            cell_alpha = min(100, self.spawn_animation_timer * 2)
            cell_surface = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(cell_surface, (*RED[:3], cell_alpha),
                           (0, 0, CELL_SIZE, CELL_SIZE))
            surface.blit(cell_surface,
                        (self.player_pos[0] * CELL_SIZE,
                         self.player_pos[1] * CELL_SIZE))
            
            # Draw the rings
            surface.blit(ring_surface, (0, 0))
            
            # Update timer
            self.spawn_animation_timer -= 1

    def get_block_count_for_level(self):
        """Calculate the number of blocks for the current level"""
        block_count = self.BASE_BLOCKS + (self.level - 1) * self.BLOCKS_PER_LEVEL
        return min(block_count, self.MAX_BLOCKS)

    def create_falling_blocks(self):
        """Create initial falling blocks, ensuring they don't trap the player"""
        max_attempts = 10
        for attempt in range(max_attempts):
            self.falling_blocks = []
            blocks_valid = True
            
            # Get block count for current level
            block_count = self.get_block_count_for_level()
            
            # Try to place blocks
            for _ in range(block_count):
                x = random.randint(0, GRID_SIZE-1)
                # Initially distribute blocks randomly throughout the map
                y = random.uniform(0, GRID_SIZE-1)
                
                # Don't place blocks directly above player or endpoint
                if x == self.player_pos[0] or x == self.endpoint[0]:
                    y = max(y, max(self.player_pos[1], self.endpoint[1]) + 2)
                
                block = FallingBlock(x, y)
                # Randomize initial fall delays more widely for initial distribution
                block.fall_delay = random.randint(0, 60)
                self.falling_blocks.append(block)
            
            # Verify this block configuration doesn't trap the player
            if not self.check_player_trapped():
                return
            
            # If we get here, the configuration was invalid
            blocks_valid = False
        
        # If we couldn't find a valid configuration, place fewer blocks
        self.falling_blocks = []
        reduced_blocks = block_count // 2
        for _ in range(reduced_blocks):
            x = random.randint(0, GRID_SIZE-1)
            # Place blocks higher up to give more time for player to move
            y = random.uniform(0, 2)
            block = FallingBlock(x, y)
            block.fall_delay = random.randint(30, 90)
            self.falling_blocks.append(block)

    def simulate_block_landing(self, block):
        """Simulate where a block will land"""
        test_y = block.y
        while test_y < GRID_SIZE - 1:
            next_y = int(test_y) + 1
            # Stop if hitting a blocking color
            if self.grid[int(block.x)][next_y] == self.colors_inverted:
                break
            # Stop if hitting another block
            block_collision = False
            for other_block in self.falling_blocks:
                if other_block != block and int(other_block.x) == int(block.x) and int(other_block.y) == next_y:
                    block_collision = True
                    break
            if block_collision:
                break
            test_y = next_y
        return int(test_y)

    def will_block_fall_here(self, x, y):
        """Check if any block will fall to this position"""
        for block in self.falling_blocks:
            if int(block.x) == x:
                if block.falling and int(block.y) < y:
                    landing_y = self.simulate_block_landing(block)
                    if landing_y == y:
                        return True
        return False

    def check_player_trapped_after_transition(self):
        """Check if player will be trapped after transition and blocks fall"""
        # First check if a block will fall on the player
        if self.will_block_fall_here(self.player_pos[0], self.player_pos[1]):
            return True
            
        # Check all four directions
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            new_x = self.player_pos[0] + dx
            new_y = self.player_pos[1] + dy
            if self.will_position_be_valid(new_x, new_y, self.endpoint):
                return False
        return True

    def is_adjacent_to_player(self, x, y):
        """Check if a position is adjacent to the player"""
        return (abs(x - self.player_pos[0]) + abs(y - self.player_pos[1])) == 1

    def update_falling_blocks(self):
        """Update the positions and states of all falling blocks"""
        blocks_moved = False
        blocks_still_transitioning = False
        check_trapped = False
        
        for block in self.falling_blocks:
            if not block.should_start_falling():
                blocks_still_transitioning = True
                continue
                
            if block.falling:
                # Store previous position
                prev_y = block.y
                prev_grid_y = int(prev_y)
                
                # Apply gravity
                block.y_velocity += GRAVITY
                # Cap maximum falling speed
                block.y_velocity = min(block.y_velocity, 0.5)
                new_y = block.y + block.y_velocity

                # Convert to grid coordinates
                grid_y = int(new_y)
                grid_x = int(block.x)
                
                # Check if block would hit bottom of screen
                if grid_y >= GRID_SIZE - 1:
                    # Check if the block can fall through to the top
                    # First, check if the space at the top is blocked
                    if self.grid[grid_x][0] == self.colors_inverted:
                        # If top is blocked, stop at bottom
                        block.y = GRID_SIZE - 1
                        block.falling = False
                        block.y_velocity = 0
                        self.sound_effects.play_block_fall()
                        blocks_moved = True
                        continue
                    
                    # Check for other blocks at the top
                    blocked_at_top = False
                    for other_block in self.falling_blocks:
                        if block != other_block and int(other_block.x) == grid_x and int(other_block.y) == 0:
                            blocked_at_top = True
                            break
                    
                    if blocked_at_top:
                        # If blocked by another block at top, stop at bottom
                        block.y = GRID_SIZE - 1
                        block.falling = False
                        block.y_velocity = 0
                        self.sound_effects.play_block_fall()
                        blocks_moved = True
                        continue
                    
                    # If not blocked, wrap to top
                    block.y = 0
                    block.y_velocity = 0
                    blocks_moved = True
                    continue

                # Check if block would hit a blocking color
                if grid_y + 1 < GRID_SIZE and self.grid[grid_x][grid_y + 1] == self.colors_inverted:
                    block.y = grid_y
                    block.falling = False
                    block.y_velocity = 0
                    self.sound_effects.play_block_fall()
                    blocks_moved = True
                    # Check if block landed adjacent to player
                    if self.is_adjacent_to_player(grid_x, grid_y):
                        check_trapped = True
                    continue

                # Check for collision with player (if not already in game over)
                if not self.game_over and (grid_x == self.player_pos[0] and 
                    (grid_y + 1 == self.player_pos[1] or 
                     (grid_y < self.player_pos[1] and new_y + 1 > self.player_pos[1]))):
                    # Block has landed on player - trigger game over
                    self.trigger_game_over(DEATH_CRUSHED)
                    # Still update block position for visual consistency
                    block.y = grid_y
                    block.falling = False
                    block.y_velocity = 0
                    self.sound_effects.play_block_fall()
                    blocks_moved = True
                    continue

                # Check for collision with other blocks
                for other_block in self.falling_blocks:
                    if block != other_block:
                        other_grid_y = int(other_block.y)
                        if (grid_x == int(other_block.x) and 
                            (grid_y + 1 == other_grid_y or 
                             (grid_y < other_grid_y and new_y + 1 > other_grid_y))):
                            block.y = grid_y
                            block.falling = False
                            block.y_velocity = 0
                            self.sound_effects.play_block_fall()
                            blocks_moved = True
                            # Check if block landed adjacent to player
                            if self.is_adjacent_to_player(grid_x, grid_y):
                                check_trapped = True
                            break
                else:
                    block.y = new_y
                    if int(block.y) != int(prev_y):
                        blocks_moved = True
                        # If block moved through a position adjacent to player, check if we need to check trapped
                        if (self.is_adjacent_to_player(grid_x, prev_grid_y) or 
                            self.is_adjacent_to_player(grid_x, grid_y)):
                            check_trapped = True
                        
        # Keep movement locked while blocks are still moving or in initial delay
        self.movement_locked = blocks_moved or blocks_still_transitioning
        
        # Check for trapped state only if blocks landed near player and we're not in transition
        if check_trapped and not self.is_transitioning and not blocks_still_transitioning and not self.game_over:
            if self.check_player_trapped():
                self.trigger_game_over(DEATH_TRAPPED)
                
        return blocks_still_transitioning

    def generate_grid(self, make_easier=False):
        """Generate the grid layout, optionally making it easier with more walkable spaces"""
        self.grid = []
        scale = 5.0 + (self.level * 0.5)
        if make_easier:
            # Adjust the noise threshold to create more walkable spaces
            noise_threshold = -0.2
        else:
            noise_threshold = 0.0
            
        for x in range(GRID_SIZE):
            row = []
            for y in range(GRID_SIZE):
                value = noise.pnoise2(x/scale, 
                                    y/scale, 
                                    octaves=1, 
                                    persistence=0.5,
                                    lacunarity=2.0,
                                    repeatx=GRID_SIZE,
                                    repeaty=GRID_SIZE,
                                    base=random.randint(0, 1000))
                # Convert to binary (True for white, False for black)
                row.append(value > noise_threshold)
            self.grid.append(row)

    def manhattan_distance(self, pos1, pos2):
        """Calculate the Manhattan distance between two grid positions"""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def is_position_safe_from_blocks(self, x, y):
        """Check if a position is safe from any initial block falls"""
        # Check if any block starts above this position
        for block in self.falling_blocks:
            if int(block.x) == x and int(block.y) < y:
                return False
        return True

    def will_position_be_valid(self, x, y, endpoint=None):
        """Check if a position will be valid after blocks fall"""
        # First check if the position is within bounds
        if not (0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE):
            return False
            
        # If it's the endpoint, it's always valid
        if endpoint is not None and (x, y) == endpoint:
            return True
            
        # Check if the position is currently blocked by the grid
        if self.grid[x][y] == self.colors_inverted:
            return False
            
        # Check if there's currently a block there
        for block in self.falling_blocks:
            if int(block.x) == x and int(block.y) == y and not block.falling:
                return False
                
        # Check if a block will fall here
        if self.will_block_fall_here(x, y):
            return False
            
        return True

    def find_valid_positions(self, min_distance):
        """Find all valid positions that are at least min_distance apart"""
        valid_positions = []
        
        # First, collect all valid positions (walkable spaces)
        for x in range(GRID_SIZE):
            for y in range(GRID_SIZE):
                # Position must be walkable and safe from initial block falls
                if self.grid[x][y] != self.colors_inverted and self.is_position_safe_from_blocks(x, y):
                    valid_positions.append((x, y))
        
        if not valid_positions:
            return None, None
            
        # Shuffle the positions for randomness
        random.shuffle(valid_positions)
        
        # Try each position as a potential player start
        for start_pos in valid_positions:
            # For each potential start position, verify it has at least one valid move
            has_valid_move = False
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                new_x = start_pos[0] + dx
                new_y = start_pos[1] + dy
                if self.will_position_be_valid(new_x, new_y):
                    has_valid_move = True
                    break
            
            if not has_valid_move:
                continue
                
            # Find a valid endpoint that's far enough away
            for end_pos in valid_positions:
                if start_pos != end_pos and self.manhattan_distance(start_pos, end_pos) >= min_distance:
                    # Also verify the endpoint is reachable (has at least one adjacent valid position)
                    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        end_adj_x = end_pos[0] + dx
                        end_adj_y = end_pos[1] + dy
                        if self.will_position_be_valid(end_adj_x, end_adj_y, end_pos):
                            return start_pos, end_pos
        
        return None, None  # No valid pair found

    # Keep old placement methods as fallback
    def place_player_old(self):
        """Original player placement method as fallback"""
        while True:
            x = random.randint(0, GRID_SIZE-1)
            y = random.randint(0, GRID_SIZE-1)
            if self.grid[x][y] != self.colors_inverted:
                self.player_pos = [x, y]
                break

    def place_endpoint_old(self):
        """Original endpoint placement method as fallback"""
        while True:
            x = random.randint(0, GRID_SIZE-1)
            y = random.randint(0, GRID_SIZE-1)
            if (x, y) != (self.player_pos[0], self.player_pos[1]) and \
               self.grid[x][y] != self.colors_inverted:
                self.endpoint = (x, y)
                break

    def is_valid_move(self, new_x, new_y):
        return self.will_position_be_valid(new_x, new_y, self.endpoint)

    def handle_movement(self, dx, dy):
        """Handle player movement"""
        # Don't allow movement during transitions or when movement is locked
        if self.is_transitioning or self.movement_locked or self.game_over:
            return False

        new_x = self.player_pos[0] + dx
        new_y = self.player_pos[1] + dy

        if self.is_valid_move(new_x, new_y):
            old_pos = self.player_pos.copy()
            self.player_pos = [new_x, new_y]
            self.sound_effects.play_move()
            # Mark that a move has been made
            self._moves_made = True
            return True
        return False

    def handle_continuous_movement(self):
        # Only process movement if cooldown has elapsed
        if self.movement_delay > 0:
            self.movement_delay -= 1
            return

        # Get current keyboard state
        keys = pygame.key.get_pressed()
        
        # Check movement keys
        moved = False
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.handle_movement(-1, 0)
            moved = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.handle_movement(1, 0)
            moved = True
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.handle_movement(0, -1)
            moved = True
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.handle_movement(0, 1)
            moved = True

        # Reset movement delay if any movement occurred
        if moved:
            self.movement_delay = self.movement_cooldown

    def draw_glow(self, surface, position, color, radius):
        """Draw a soft glow effect"""
        x, y = position
        glow_surf = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
        
        for i in range(3):
            pygame.draw.circle(glow_surf, (*color[:3], 20),
                             (radius * 2, radius * 2), radius * (1.5 - i * 0.2))
        
        surface.blit(glow_surf, (x - radius * 2, y - radius * 2))

    def draw_rounded_rect(self, surface, color, rect, radius):
        """Draw a rectangle with rounded corners"""
        pygame.draw.rect(surface, color, rect.inflate(-radius * 2, 0))
        pygame.draw.rect(surface, color, rect.inflate(0, -radius * 2))
        
        for corner in [(rect.topleft, rect.topright, rect.bottomright, rect.bottomleft)]:
            for x, y in corner:
                pygame.draw.circle(surface, color, (x, y), radius)

    def draw_portal(self, surface, x, y, tick):
        """Draw an animated portal for the exit"""
        radius = PLAYER_SIZE // 2
        inner_radius = radius * 0.7
        
        # Outer circle (static)
        pygame.draw.circle(surface, PORTAL_COLORS[0], (x, y), radius)
        
        # Inner circle (pulsing)
        pulse = math.sin(tick * 0.1) * 0.2 + 0.8
        inner_radius = int(inner_radius * pulse)
        pygame.draw.circle(surface, PORTAL_COLORS[1], (x, y), inner_radius)
        
        # Add some "sparkles" rotating around the portal
        for i in range(3):
            angle = tick * 0.1 + (i * 2 * math.pi / 3)
            sparkle_x = x + int(math.cos(angle) * radius * 0.8)
            sparkle_y = y + int(math.sin(angle) * radius * 0.8)
            pygame.draw.circle(surface, WHITE, (sparkle_x, sparkle_y), 2)

    def draw_player(self, surface, x, y):
        """Draw the player as a @ symbol with a glow effect"""
        # Draw the glow
        self.draw_glow(surface, (x, y), PLAYER_GLOW, PLAYER_SIZE // 2)
        
        # Render the @ symbol
        text_color = RED
        player_text = self.player_font.render("@", True, text_color)
        
        # Center the text in the cell
        text_rect = player_text.get_rect(center=(x, y))
        
        # Draw the text
        surface.blit(player_text, text_rect)

    def draw_level_announcement(self, surface):
        """Draw the level announcement during transitions"""
        if self.is_level_transitioning:
            # Only show number during fadeout and hold, not during fadein
            if self.level_transition_state == 'fadeout' or self.transition_hold_timer > 0:
                # Calculate alpha based on transition progress
                if self.level_transition_state == 'fadeout':
                    # Fade in with the background fade
                    text_alpha = self.level_transition_alpha
                else:
                    text_alpha = 255
                
                # Create text surfaces
                level_text = self.level_announcement_small_font.render("LEVEL", True, 
                                                                     WHITE if self.colors_inverted else BLACK)
                number_text = self.level_announcement_font.render(str(self.next_level), True, 
                                                               WHITE if self.colors_inverted else BLACK)
                
                # Calculate positions
                center_x = WINDOW_SIZE // 2
                center_y = WINDOW_SIZE // 2
                
                # Get text rectangles
                level_rect = level_text.get_rect(centerx=center_x, bottom=center_y - 5)
                number_rect = number_text.get_rect(centerx=center_x, top=center_y + 5)
                
                # Create a surface for the announcement
                announcement_surface = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
                
                # Set alpha for the text
                level_text.set_alpha(text_alpha)
                number_text.set_alpha(text_alpha)
                
                # Draw texts
                announcement_surface.blit(level_text, level_rect)
                announcement_surface.blit(number_text, number_rect)
                
                # Draw the announcement
                surface.blit(announcement_surface, (0, 0))

    def draw_direction_indicator(self, surface):
        """Draw an arrow pointing from the player to the portal"""
        if not self.is_level_transitioning:
            # Calculate centers of player and portal
            player_x = self.player_pos[0] * CELL_SIZE + CELL_SIZE // 2
            player_y = self.player_pos[1] * CELL_SIZE + CELL_SIZE // 2
            portal_x = self.endpoint[0] * CELL_SIZE + CELL_SIZE // 2
            portal_y = self.endpoint[1] * CELL_SIZE + CELL_SIZE // 2

            # Calculate direction vector
            dx = portal_x - player_x
            dy = portal_y - player_y
            
            # Normalize the vector
            length = math.sqrt(dx * dx + dy * dy)
            if length > 0:
                dx /= length
                dy /= length
                
                # Calculate end point of indicator
                end_x = player_x + dx * INDICATOR_LENGTH
                end_y = player_y + dy * INDICATOR_LENGTH
                
                # Create a surface for the indicator with alpha channel
                indicator_surface = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
                
                # Draw the main line
                pygame.draw.line(indicator_surface, INDICATOR_COLOR,
                               (player_x, player_y), (end_x, end_y), INDICATOR_WIDTH)
                
                # Calculate arrow head points
                arrow_angle = math.pi / 6
                head_length = INDICATOR_HEAD_SIZE
                
                # Calculate the angle of the main line
                angle = math.atan2(dy, dx)
                
                # Calculate arrow head points
                head_left = (
                    end_x - head_length * math.cos(angle + arrow_angle),
                    end_y - head_length * math.sin(angle + arrow_angle)
                )
                head_right = (
                    end_x - head_length * math.cos(angle - arrow_angle),
                    end_y - head_length * math.sin(angle - arrow_angle)
                )
                
                # Draw arrow head
                pygame.draw.polygon(indicator_surface, INDICATOR_COLOR,
                                  [(end_x, end_y), head_left, head_right])
                
                # Add a pulsing effect based on animation tick
                pulse = abs(math.sin(self.animation_tick * 0.05)) * 0.4 + 0.6
                indicator_surface.set_alpha(int(160 * pulse))
                
                # Draw the indicator
                surface.blit(indicator_surface, (0, 0))

    def check_player_trapped(self):
        """Check if the player has no valid moves in their current position"""
        # Don't check for trapped state during any kind of transition
        if self.is_transitioning:
            return False
            
        # First check if a block will fall on the player
        if self.will_block_fall_here(self.player_pos[0], self.player_pos[1]):
            # If no moves have been made yet, don't consider this trapped
            if not hasattr(self, '_moves_made'):
                self._moves_made = False
                return False
            return True
            
        # Check all four directions
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            new_x = self.player_pos[0] + dx
            new_y = self.player_pos[1] + dy
            if self.will_position_be_valid(new_x, new_y, self.endpoint):
                return False
        return True

    def trigger_game_over(self, reason):
        """Trigger the game over state with a specific reason"""
        self.game_over = True
        self.game_over_alpha = 0
        self.game_over_reason = reason
        self.death_animation_timer = self.death_animation_duration
        
        # Create death particles
        num_particles = 12
        for i in range(num_particles):
            angle = (i / num_particles) * 2 * math.pi
            speed = random.uniform(2, 4)
            self.death_particles.append({
                'x': self.player_pos[0] * CELL_SIZE + CELL_SIZE // 2,
                'y': self.player_pos[1] * CELL_SIZE + CELL_SIZE // 2,
                'dx': math.cos(angle) * speed,
                'dy': math.sin(angle) * speed,
                'alpha': 255,
                'size': random.randint(3, 6)
            })

    def update_death_animation(self):
        """Update death animation particles"""
        if self.death_animation_timer > 0:
            self.death_animation_timer -= 1
            
            # Update particles
            for particle in self.death_particles:
                particle['x'] += particle['dx']
                particle['y'] += particle['dy']
                particle['dy'] += 0.2  # Gravity
                particle['alpha'] = max(0, particle['alpha'] - 4)  # Fade out

    def draw_death_animation(self, surface):
        """Draw the death animation"""
        if self.death_animation_timer > 0:
            # Draw particles
            for particle in self.death_particles:
                if particle['alpha'] > 0:
                    particle_surface = pygame.Surface((particle['size'], particle['size']), pygame.SRCALPHA)
                    particle_color = (*RED[:3], particle['alpha'])
                    pygame.draw.circle(particle_surface, particle_color,
                                    (particle['size']//2, particle['size']//2),
                                    particle['size']//2)
                    surface.blit(particle_surface,
                               (particle['x'] - particle['size']//2,
                                particle['y'] - particle['size']//2))

    def draw_game_over(self, surface):
        """Draw the game over screen"""
        if not self.game_over:
            return

        # Increase alpha for fade-in effect
        self.game_over_alpha = min(255, self.game_over_alpha + 5)
        
        # Create a surface for the game over display
        overlay = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
        
        # Draw semi-transparent background
        overlay.fill((0, 0, 0, min(180, self.game_over_alpha)))
        
        # Draw "GAME OVER" text
        game_over_text = self.game_over_font.render("GAME OVER", True, GAME_OVER_COLOR)
        text_rect = game_over_text.get_rect(center=(WINDOW_SIZE // 2, WINDOW_SIZE // 2 - 60))
        game_over_text.set_alpha(self.game_over_alpha)
        overlay.blit(game_over_text, text_rect)
        
        # Draw reason text
        reason_text = self.restart_font.render(self.game_over_reason, True, GAME_OVER_COLOR)
        reason_rect = reason_text.get_rect(center=(WINDOW_SIZE // 2, WINDOW_SIZE // 2 - 20))
        reason_text.set_alpha(self.game_over_alpha)
        overlay.blit(reason_text, reason_rect)
        
        # Draw level reached text
        level_text = self.restart_font.render(f"You reached Level {self.level}", True, RESTART_TEXT_COLOR)
        level_rect = level_text.get_rect(center=(WINDOW_SIZE // 2, WINDOW_SIZE // 2 + 20))
        level_text.set_alpha(self.game_over_alpha)
        overlay.blit(level_text, level_rect)
        
        # Draw restart instruction
        restart_text = self.restart_font.render("Press R to restart", True, RESTART_TEXT_COLOR)
        restart_rect = restart_text.get_rect(center=(WINDOW_SIZE // 2, WINDOW_SIZE // 2 + 60))
        restart_text.set_alpha(self.game_over_alpha)
        overlay.blit(restart_text, restart_rect)
        
        # Draw the overlay
        surface.blit(overlay, (0, 0))

    def draw_movement_lock_indicator(self, surface):
        """Draw an indicator when movement is locked during transition"""
        if not (self.is_transitioning or self.showing_contrast_preview or self.movement_locked) or self.game_over:
            return
            
        # Get player's current grid position
        px, py = self.player_pos
        
        # Create a surface for the indicator
        cell_surface = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        
        # Draw the lock indicator
        pygame.draw.rect(cell_surface, MOVEMENT_LOCK_COLOR,
                        (0, 0, CELL_SIZE, CELL_SIZE))
        pygame.draw.rect(cell_surface, MOVEMENT_LOCK_BORDER,
                        (0, 0, CELL_SIZE, CELL_SIZE), 2)
        
        # Draw small lock symbols or arrows in each direction
        arrow_length = CELL_SIZE // 4
        center_x = CELL_SIZE // 2
        center_y = CELL_SIZE // 2
        
        # Draw crossed lines to indicate movement is locked
        for offset in [-arrow_length, arrow_length]:
            pygame.draw.line(cell_surface, MOVEMENT_LOCK_BORDER,
                           (center_x + offset, center_y - arrow_length),
                           (center_x + offset, center_y + arrow_length), 2)
            pygame.draw.line(cell_surface, MOVEMENT_LOCK_BORDER,
                           (center_x - arrow_length, center_y + offset),
                           (center_x + arrow_length, center_y + offset), 2)
        
        # Draw the indicator at player position
        surface.blit(cell_surface, 
                    (px * CELL_SIZE, py * CELL_SIZE))

    def draw_danger_indicators(self, surface):
        """Draw indicators for dangerous and invalid positions"""
        if self.game_over or self.is_level_transitioning:
            return
            
        # Get player's current grid position
        px, py = self.player_pos
        
        # Check each adjacent position
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            new_x = px + dx
            new_y = py + dy
            
            # Skip if out of bounds
            if not (0 <= new_x < GRID_SIZE and 0 <= new_y < GRID_SIZE):
                continue
                
            # Create a surface for this cell
            cell_surface = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            
            # If showing contrast preview, check validity after contrast switch
            if self.showing_contrast_preview:
                self.colors_inverted = not self.colors_inverted
                is_valid = self.will_position_be_valid(new_x, new_y, self.endpoint)
                self.colors_inverted = not self.colors_inverted
                
                if not is_valid:
                    # Draw invalid move indicator
                    pygame.draw.rect(cell_surface, INVALID_MOVE_COLOR, 
                                   (0, 0, CELL_SIZE, CELL_SIZE))
            
            # Check if position is currently valid
            if not self.will_position_be_valid(new_x, new_y, self.endpoint):
                # Draw danger indicator
                pygame.draw.rect(cell_surface, DANGER_COLOR,
                               (0, 0, CELL_SIZE, CELL_SIZE))
                pygame.draw.rect(cell_surface, DANGER_BORDER,
                               (0, 0, CELL_SIZE, CELL_SIZE), 2)
            
            # Draw the indicator
            surface.blit(cell_surface, 
                        (new_x * CELL_SIZE, new_y * CELL_SIZE))

    def reset_game_state(self):
        """Reset the entire game state to start over"""
        self.level = 1
        self.next_level = 1  # Reset next_level to match current level
        self.colors_inverted = False
        self.game_over = False
        self.game_over_alpha = 0
        self.death_animation_timer = 0
        self.death_particles = []
        self.is_transitioning = False
        self.is_level_transitioning = True  # Start with level transition
        self.level_transition_state = 'fadeout'  # Start with fadeout to show level 1
        self.level_transition_alpha = 0
        self.transition_hold_timer = self.transition_hold_duration
        self.reset_game()

    def draw_menu_text(self, text, font, color, y_pos, selected=False, disabled=False, center_x=None):
        """Helper method to draw menu text with optional selection highlight and custom x position"""
        if disabled:
            color = tuple(c // 2 for c in color[:3]) + (color[3],) if len(color) > 3 else tuple(c // 2 for c in color)
        text_surface = font.render(text, True, color)
        if center_x is None:
            center_x = WINDOW_SIZE // 2
        text_rect = text_surface.get_rect(center=(center_x, y_pos))
        
        if selected and not disabled:
            # Draw selection indicator
            arrow_points = [
                (text_rect.left - 30, y_pos),
                (text_rect.left - 20, y_pos - 10),
                (text_rect.left - 20, y_pos + 10)
            ]
            pygame.draw.polygon(self.screen, MENU_SELECTED, arrow_points)
        
        self.screen.blit(text_surface, text_rect)
        return text_rect

    def draw_intro_menu(self):
        """Draw the intro menu"""
        bg_surface = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
        bg_surface.fill(MENU_BG)
        self.screen.blit(bg_surface, (0, 0))
        
        # Title
        self.draw_menu_text("The Inverse Path", self.title_font, MENU_TITLE, WINDOW_SIZE // 4)
        
        # Menu items
        menu_items = [
            "Start Game",
            "Tutorial",
            "Options",
            "Quit"
        ]
        start_y = WINDOW_SIZE // 2
        spacing = 60
        
        for i, item in enumerate(menu_items):
            self.draw_menu_text(item, self.menu_font, MENU_TEXT if i != self.selected_menu_item else MENU_HIGHLIGHT,
                              start_y + i * spacing, selected=(i == self.selected_menu_item))

    def draw_pause_menu(self):
        """Draw the pause menu"""
        # Draw game state in background (dimmed)
        bg_surface = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
        bg_surface.fill(MENU_BG)
        self.screen.blit(bg_surface, (0, 0))
        
        # Draw "PAUSED" text
        self.draw_menu_text("PAUSED", self.title_font, MENU_TITLE, WINDOW_SIZE // 3)
        
        # Menu items
        menu_items = ["Resume", "Options", "Quit to Menu"]
        start_y = WINDOW_SIZE // 2
        spacing = 60
        
        for i, item in enumerate(menu_items):
            self.draw_menu_text(item, self.menu_font, MENU_TEXT if i != self.selected_menu_item else MENU_HIGHLIGHT,
                              start_y + i * spacing, selected=(i == self.selected_menu_item))

    def draw_options_menu(self):
        """Draw the options menu"""
        bg_surface = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
        bg_surface.fill(MENU_BG)
        self.screen.blit(bg_surface, (0, 0))
        
        # Title
        self.draw_menu_text("Options", self.title_font, MENU_TITLE, WINDOW_SIZE // 4)
        
        # Menu items with current values
        menu_items = [
            f"SFX Volume: {'Muted' if self.sfx_muted else int(self.sfx_volume * 100)}%",
            f"Music Volume: {'Muted' if self.music_muted else int(self.music_volume * 100)}%",
            "Keybindings",
            "Back"
        ]
        start_y = WINDOW_SIZE // 2
        spacing = 60
        
        for i, item in enumerate(menu_items):
            self.draw_menu_text(item, self.menu_font, MENU_TEXT if i != self.selected_menu_item else MENU_HIGHLIGHT,
                              start_y + i * spacing, selected=(i == self.selected_menu_item))

    def draw_keybind_menu(self):
        """Draw the key rebinding menu"""
        bg_surface = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
        bg_surface.fill(MENU_BG)
        self.screen.blit(bg_surface, (0, 0))
        
        # Title
        self.draw_menu_text("Keybindings", self.title_font, MENU_TITLE, WINDOW_SIZE // 4)
        
        # Create menu items from keybindings
        menu_items = []
        for action, keys in self.keybindings.items():
            if isinstance(keys, list):
                key_names = [pygame.key.name(k).upper() for k in keys]
                menu_items.append(f"{action.title()}: {' or '.join(key_names)}")
            else:
                menu_items.append(f"{action.title()}: {pygame.key.name(keys).upper()}")
        menu_items.append("Back")
        
        start_y = WINDOW_SIZE // 2
        spacing = 45
        
        for i, item in enumerate(menu_items):
            is_selected = i == self.selected_menu_item
            is_waiting = self.waiting_for_key is not None and i == self.waiting_for_key
            text_color = MENU_SELECTED if is_waiting else (MENU_HIGHLIGHT if is_selected else MENU_TEXT)
            self.draw_menu_text(item, self.submenu_font, text_color,
                              start_y + i * spacing, selected=is_selected)

    def handle_menu_input(self, event):
        """Handle menu navigation and selection"""
        if event.type == pygame.KEYDOWN:
            if event.key in self.keybindings["up"]:
                self.selected_menu_item = (self.selected_menu_item - 1) % self.get_menu_item_count()
                self.sound_effects.play_move()
            elif event.key in self.keybindings["down"]:
                self.selected_menu_item = (self.selected_menu_item + 1) % self.get_menu_item_count()
                self.sound_effects.play_move()
            elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                self.handle_menu_selection()
            elif event.key == pygame.K_ESCAPE:
                if self.menu_state == MENU_PAUSE:
                    self.menu_state = MENU_GAME
                elif self.menu_state == MENU_OPTIONS:
                    self.menu_state = self.previous_menu
                    self.selected_menu_item = 0
                elif self.menu_state == MENU_KEYBIND:
                    self.menu_state = MENU_OPTIONS
                    self.selected_menu_item = 0
                self.selected_menu_item = 0
            # Handle volume adjustments in options menu
            elif self.menu_state == MENU_OPTIONS and self.selected_menu_item in [0, 1]:
                if event.key in self.keybindings["left"]:
                    if self.selected_menu_item == 0:
                        self.sfx_volume = max(0.0, self.sfx_volume - 0.1)
                        self.sound_effects.set_volume(self.sfx_volume)
                        if not self.sfx_muted:
                            self.sound_effects.play_move()
                    else:
                        self.music_volume = max(0.0, self.music_volume - 0.1)
                        self.music_gen.set_volume(self.music_volume)
                elif event.key in self.keybindings["right"]:
                    if self.selected_menu_item == 0:
                        self.sfx_volume = min(1.0, self.sfx_volume + 0.1)
                        self.sound_effects.set_volume(self.sfx_volume)
                        if not self.sfx_muted:
                            self.sound_effects.play_move()
                    else:
                        self.music_volume = min(1.0, self.music_volume + 0.1)
                        self.music_gen.set_volume(self.music_volume)

    def get_menu_item_count(self):
        """Get the number of items in the current menu"""
        if self.menu_state == MENU_INTRO:
            return 4
        elif self.menu_state == MENU_PAUSE:
            return 3
        elif self.menu_state == MENU_OPTIONS:
            return 4
        elif self.menu_state == MENU_KEYBIND:
            return len(self.keybindings) + 1
        elif self.menu_state == MENU_TUTORIAL:
            return 1
        return 0

    def handle_menu_selection(self):
        """Handle menu item selection"""
        if self.menu_state == MENU_INTRO:
            if self.selected_menu_item == 0:
                self.menu_state = MENU_GAME
                self.reset_game_state()
            elif self.selected_menu_item == 1:
                self.previous_menu = MENU_INTRO
                self.menu_state = MENU_TUTORIAL
                self.selected_menu_item = 0
            elif self.selected_menu_item == 2:
                self.previous_menu = MENU_INTRO
                self.menu_state = MENU_OPTIONS
                self.selected_menu_item = 0
            elif self.selected_menu_item == 3:
                self.clean_up()
                pygame.quit()
                sys.exit()
        
        elif self.menu_state == MENU_PAUSE:
            if self.selected_menu_item == 0:
                self.menu_state = MENU_GAME
            elif self.selected_menu_item == 1:
                self.previous_menu = MENU_PAUSE
                self.menu_state = MENU_OPTIONS
                self.selected_menu_item = 0
            elif self.selected_menu_item == 2:
                self.clean_up_game_state()
                self.menu_state = MENU_INTRO
                self.selected_menu_item = 0
                self.reset_game_state()
        
        elif self.menu_state == MENU_OPTIONS:
            if self.selected_menu_item == 0:
                self.sfx_muted = not self.sfx_muted
                self.sound_effects.set_muted(self.sfx_muted)
                if not self.sfx_muted:
                    self.sound_effects.play_move()
            elif self.selected_menu_item == 1:
                self.music_muted = not self.music_muted
                self.music_gen.set_muted(self.music_muted)
                if not self.music_muted and not self.music_thread.is_alive():
                    self.start_background_music()
            elif self.selected_menu_item == 2:
                self.menu_state = MENU_KEYBIND
                self.selected_menu_item = 0
            elif self.selected_menu_item == 3:
                self.menu_state = self.previous_menu
                self.selected_menu_item = 0
                
        elif self.menu_state == MENU_KEYBIND:
            if self.selected_menu_item == len(self.keybindings):
                self.menu_state = MENU_OPTIONS
                self.selected_menu_item = 0
            else:
                self.waiting_for_key = self.selected_menu_item

        elif self.menu_state == MENU_TUTORIAL:
            if self.selected_menu_item == 0:
                self.menu_state = self.previous_menu
                self.selected_menu_item = 0

    def handle_keybind_input(self, event):
        """Handle key rebinding input"""
        if self.waiting_for_key is not None and event.type == pygame.KEYDOWN:
            if event.key != pygame.K_ESCAPE:
                # Get the action being rebound
                action = list(self.keybindings.keys())[self.waiting_for_key]
                # Update the keybinding
                if isinstance(self.keybindings[action], list):
                    self.keybindings[action] = [event.key]
                else:
                    self.keybindings[action] = event.key
            self.waiting_for_key = None

    def get_key_name(self, key_or_list):
        """Get a readable name for a key or list of keys"""
        if isinstance(key_or_list, list):
            return '/'.join(pygame.key.name(k).upper() for k in key_or_list)
        return pygame.key.name(key_or_list).upper()

    def draw_tutorial_menu(self):
        """Draw the tutorial/help menu with visual examples and explanations"""
        # Draw background
        bg_surface = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
        bg_surface.fill(MENU_BG)
        self.screen.blit(bg_surface, (0, 0))
        
        # Title
        self.draw_menu_text("How to Play", self.title_font, MENU_TITLE, 60)
        
        # Layout constants
        left_column = WINDOW_SIZE // 4
        right_column = WINDOW_SIZE * 3 // 4
        current_y = 120
        section_height = 100
        
        # Player Section
        self.draw_menu_text("The Player", self.menu_font, MENU_SECTION_TITLE, current_y)
        current_y += 40
        # Player description (left side)
        player_desc = "You control the @ symbol."
        controls_desc = "Use arrow keys or WASD to move."
        text_y = current_y + PLAYER_SIZE // 2
        self.draw_menu_text(player_desc, self.submenu_font, MENU_DESCRIPTION, text_y - 15, center_x=left_column)
        self.draw_menu_text(controls_desc, self.submenu_font, MENU_DESCRIPTION, text_y + 15, center_x=left_column)
        # Draw player example (right side)
        self.draw_player(self.screen, right_column, current_y + section_height // 3)
        
        current_y += section_height
        
        # Exit Portal Section
        self.draw_menu_text("The Exit", self.menu_font, MENU_SECTION_TITLE, current_y)
        current_y += 40
        # Portal description (left side)
        portal_desc = "Reach the blue portal to"
        portal_desc2 = "complete each level."
        text_y = current_y + PLAYER_SIZE // 2
        self.draw_menu_text(portal_desc, self.submenu_font, MENU_DESCRIPTION, text_y - 15, center_x=left_column)
        self.draw_menu_text(portal_desc2, self.submenu_font, MENU_DESCRIPTION, text_y + 15, center_x=left_column)
        # Draw portal example (right side)
        self.draw_portal(self.screen, right_column, current_y + section_height // 3, self.animation_tick)
        
        current_y += section_height
        
        # Falling Blocks Section
        self.draw_menu_text("Falling Blocks", self.menu_font, MENU_SECTION_TITLE, current_y)
        current_y += 40
        # Block description (left side)
        block_desc = "Grey blocks fall when"
        block_desc2 = "unsupported. Don't get trapped!"
        text_y = current_y + PLAYER_SIZE // 2
        self.draw_menu_text(block_desc, self.submenu_font, MENU_DESCRIPTION, text_y - 15, center_x=left_column)
        self.draw_menu_text(block_desc2, self.submenu_font, MENU_DESCRIPTION, text_y + 15, center_x=left_column)
        # Draw block example (right side)
        block_rect = pygame.Rect(right_column - PLAYER_SIZE // 2,
                               current_y + section_height // 3 - PLAYER_SIZE // 2,
                               PLAYER_SIZE, PLAYER_SIZE)
        self.draw_rounded_rect(self.screen, BLOCK_COLOR, block_rect, 5)
        
        current_y += section_height
        
        # Contrast Section
        self.draw_menu_text("Color Switching", self.menu_font, MENU_SECTION_TITLE, current_y)
        current_y += 40
        # Contrast description (left side)
        contrast_desc = f"Press {self.get_key_name(self.keybindings['contrast'])} to"
        contrast_desc2 = "invert black and white blocks."
        contrast_desc3 = "You can move on white spaces."
        text_y = current_y + PLAYER_SIZE // 2
        self.draw_menu_text(contrast_desc, self.submenu_font, MENU_DESCRIPTION, text_y - 15, center_x=left_column)
        self.draw_menu_text(contrast_desc2, self.submenu_font, MENU_DESCRIPTION, text_y + 15, center_x=left_column)
        self.draw_menu_text(contrast_desc3, self.submenu_font, MENU_DESCRIPTION, text_y + 45, center_x=left_column)
        # Draw contrast example boxes (right side)
        box_size = PLAYER_SIZE
        box_y = current_y + section_height // 2.5 - box_size // 2
        pygame.draw.rect(self.screen, WHITE, 
                        (right_column - box_size - 5, box_y, box_size, box_size))
        pygame.draw.rect(self.screen, BLACK,
                        (right_column + 5, box_y, box_size, box_size))
        
        # Back option at bottom
        self.draw_menu_text("Back", self.menu_font, 
                           MENU_HIGHLIGHT if self.selected_menu_item == 0 else MENU_TEXT,
                           WINDOW_SIZE - 60, selected=(self.selected_menu_item == 0))

    def clean_up(self):
        """Clean up game-specific resources"""
        # First clean up game state
        self.clean_up_game_state()
        
        # Stop the music thread and wait for it to finish
        if self.music_thread and self.music_thread.is_alive():
            # Signal the music generator to stop all sounds and threads
            if hasattr(self.music_gen, 'stop_all_sounds'):
                self.music_gen.stop_all_sounds()
            
            # Set the stop event
            self.music_stop_event.set()
            
            # Give the thread a moment to clean up
            try:
                self.music_thread.join(timeout=0.5)
            except:
                pass

        # Clean up objects (this will trigger their __del__ methods if defined)
        self.sound_effects = None
        self.music_gen = None
        self.music_thread = None
        self.music_stop_event = None

    def clean_up_game_state(self):
        """Clean up game-specific resources when transitioning to menu"""
        # Stop any ongoing sounds
        if self.sound_effects:
            self.sound_effects.stop_all_sounds()
        
        # Reset game variables
        self.game_over = False
        self.is_transitioning = False
        self.is_level_transitioning = False
        self.showing_contrast_preview = False
        self.movement_locked = False
        
        # Clear any ongoing animations
        self.death_animation_timer = 0
        self.death_particles = []
        self.spawn_rings = []

    def run(self):
        """Main game loop"""
        running = True
        blocks_settling = False
        transition_complete = False

        try:
            while running and not _is_shutting_down:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                        break
                    elif self.menu_state != MENU_GAME:
                        # Handle menu input
                        if self.waiting_for_key is not None:
                            self.handle_keybind_input(event)
                        else:
                            self.handle_menu_input(event)
                    else:
                        # Game input handling
                        if event.type == pygame.KEYDOWN:
                            if event.key == self.keybindings["pause"]:
                                self.menu_state = MENU_PAUSE
                                self.selected_menu_item = 0
                            elif event.key == self.keybindings["restart"] and self.game_over:
                                self.reset_game_state()
                            elif event.key == self.keybindings["contrast"] and not self.is_transitioning and not self.game_over:
                                self.showing_contrast_preview = True
                                self.preview_alpha = 0
                        elif event.type == pygame.KEYUP:
                            if event.key == self.keybindings["contrast"]:
                                if self.showing_contrast_preview and not self.game_over:
                                    self.showing_contrast_preview = False
                                    self.colors_inverted = not self.colors_inverted
                                    trapped_after_switch = self.check_player_trapped_after_transition()
                                    self.colors_inverted = not self.colors_inverted

                                    if not trapped_after_switch:
                                        self.is_transitioning = True
                                        blocks_settling = False
                                        self.sound_effects.play_contrast_shift()
                                self.showing_contrast_preview = False

                if not running:
                    break
                    
                # Draw the base game state
                self.screen.fill(BLACK if self.colors_inverted else WHITE)
                
                # Draw grid
                for x in range(GRID_SIZE):
                    for y in range(GRID_SIZE):
                        cell_color = WHITE if self.grid[x][y] != self.colors_inverted else BLACK
                        pygame.draw.rect(self.screen, cell_color, 
                                       (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE))
                        pygame.draw.rect(self.screen, GRID_COLOR, 
                                       (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE), 1)

                if self.menu_state == MENU_GAME:
                    # Game state updates
                    if not self.game_over:
                        # Handle continuous movement
                        keys = pygame.key.get_pressed()
                        moved = False
                        if not (self.is_transitioning or self.showing_contrast_preview or self.movement_locked):
                            if self.movement_delay <= 0:
                                for direction, key_list in [
                                    ("left", [pygame.K_LEFT, pygame.K_a]),
                                    ("right", [pygame.K_RIGHT, pygame.K_d]),
                                    ("up", [pygame.K_UP, pygame.K_w]),
                                    ("down", [pygame.K_DOWN, pygame.K_s])
                                ]:
                                    if any(keys[k] for k in self.keybindings[direction]):
                                        dx = 1 if direction == "right" else -1 if direction == "left" else 0
                                        dy = 1 if direction == "down" else -1 if direction == "up" else 0
                                        self.handle_movement(dx, dy)
                                        moved = True

                                if moved:
                                    self.movement_delay = self.movement_cooldown
                            else:
                                self.movement_delay -= 1

                        # Update falling blocks
                        blocks_still_transitioning = self.update_falling_blocks()
                        
                        if blocks_settling:
                            if not blocks_still_transitioning:
                                blocks_settling = False

                        # Update contrast preview
                        if self.showing_contrast_preview:
                            self.preview_alpha = min(40, self.preview_alpha + self.preview_fade_speed)

                        # Handle contrast transition
                        if self.is_transitioning:
                            self.transition_alpha += self.transition_speed
                            if self.transition_alpha >= 100:
                                self.colors_inverted = not self.colors_inverted
                                self.transition_alpha = 0
                                self.is_transitioning = False
                                for block in self.falling_blocks:
                                    block.falling = True
                                    block.y_velocity = 0
                                blocks_settling = True
                                self.movement_locked = True

                        # Handle level transition
                        if self.is_level_transitioning:
                            if self.transition_hold_timer > 0:
                                self.transition_hold_timer -= 1
                            else:
                                if self.level_transition_state == 'fadeout':
                                    self.level_transition_alpha += self.level_transition_speed
                                    if self.level_transition_alpha >= 255:
                                        self.level = self.next_level
                                        self.reset_game()
                                        self.level_transition_state = 'fadein'
                                        self.transition_hold_timer = self.transition_hold_duration
                                elif self.level_transition_state == 'fadein':
                                    self.level_transition_alpha -= self.level_transition_speed
                                    if self.level_transition_alpha <= 0:
                                        self.level_transition_alpha = 0
                                        self.is_level_transitioning = False
                                        self.level_transition_state = 'none'
                                        self.start_spawn_animation()

                        # Check if player reached endpoint
                        if (self.player_pos[0], self.player_pos[1]) == self.endpoint and not self.is_level_transitioning:
                            self.sound_effects.play_victory()
                            self.is_level_transitioning = True
                            self.level_transition_state = 'fadeout'
                            self.level_transition_alpha = 0
                            self.next_level = self.level + 1
                            self.transition_hold_timer = self.transition_hold_duration

                    # Draw game elements
                    self.draw_spawn_animation(self.screen)
                    endpoint_x = self.endpoint[0] * CELL_SIZE + CELL_SIZE // 2
                    endpoint_y = self.endpoint[1] * CELL_SIZE + CELL_SIZE // 2
                    self.draw_glow(self.screen, (endpoint_x, endpoint_y), ENDPOINT_GLOW, PLAYER_SIZE)
                    self.draw_portal(self.screen, endpoint_x, endpoint_y, self.animation_tick)

                    for block in self.falling_blocks:
                        block_rect = pygame.Rect(block.x * CELL_SIZE + 4,
                                               block.y * CELL_SIZE + 4,
                                               PLAYER_SIZE, PLAYER_SIZE)
                        self.draw_rounded_rect(self.screen, BLOCK_COLOR, block_rect, 5)

                    self.draw_direction_indicator(self.screen)
                    self.draw_danger_indicators(self.screen)

                    if not self.game_over or self.death_animation_timer > 0:
                        player_x = self.player_pos[0] * CELL_SIZE + CELL_SIZE // 2
                        player_y = self.player_pos[1] * CELL_SIZE + CELL_SIZE // 2
                        self.draw_player(self.screen, player_x, player_y)

                    self.draw_movement_lock_indicator(self.screen)

                    if self.showing_contrast_preview:
                        preview_surface = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
                        preview_color = (*DANGER_COLOR[:3], self.preview_alpha)
                        preview_surface.fill(preview_color)
                        self.screen.blit(preview_surface, (0, 0))

                    if self.is_transitioning:
                        self.transition_surface.fill((255, 255, 255, self.transition_alpha))
                        self.screen.blit(self.transition_surface, (0, 0))

                    if self.is_level_transitioning:
                        self.level_transition_surface.fill(BLACK if self.colors_inverted else WHITE)
                        self.level_transition_surface.set_alpha(self.level_transition_alpha)
                        self.screen.blit(self.level_transition_surface, (0, 0))

                    self.draw_level_announcement(self.screen)
                    self.draw_game_over(self.screen)
                    self.draw_death_animation(self.screen)

                    # Update death animation
                    if self.death_animation_timer > 0:
                        self.update_death_animation()

                # Draw appropriate menu
                elif self.menu_state == MENU_INTRO:
                    self.draw_intro_menu()
                elif self.menu_state == MENU_PAUSE:
                    self.draw_pause_menu()
                elif self.menu_state == MENU_OPTIONS:
                    self.draw_options_menu()
                elif self.menu_state == MENU_KEYBIND:
                    self.draw_keybind_menu()
                elif self.menu_state == MENU_TUTORIAL:
                    self.draw_tutorial_menu()

                pygame.display.flip()
                self.clock.tick(FPS)

        except Exception as e:
            print(f"Error during game execution: {e}")
        finally:
            self.clean_up()

if __name__ == "__main__":
    game = Game()
    try:
        game.run()
    finally:
        sys.exit(0) 
