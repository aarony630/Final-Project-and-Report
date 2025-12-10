# dodge_game.py

# DODGE game — player controls the dot (tilt) and dodges a falling claw (enemy).

# Now with MULTIPLAYER mode where opponent controls the claw!

 

import time

import random

import board

import busio

import displayio

import terminalio

import digitalio

import neopixel

import pwmio

import storage

import microcontroller

from adafruit_display_text import label

import i2cdisplaybus

import adafruit_displayio_ssd1306

import adafruit_adxl34x

 

# --------------------

# CONFIG

# --------------------

SCREEN_WIDTH = 128

SCREEN_HEIGHT = 64

 

CLAW_WIDTH = 40

CLAW_Y1_BASE = 2

CLAW_Y2_BASE = 12

CLAW_Y3_BASE = 22

 

INITIAL_CLAW_SPEED = 3

CLAW_SPEED_STEP = 0.25

CLAW_RESET_Y = -10

 

DROP_STEPS = 10

DROP_STEP_PIXELS = 3

 

ACCEL_MIN = -9.0

ACCEL_MAX = 9.0

 

PLAYER_WIDTH = 8

PLAYER_Y = 52

 

LEVEL_DATA = [

    3.0, 5.0, 7.0, 10.0, 13.0,

    15.0, 17.0, 15.0, 13.0, 10.0

]

 

DIFFICULTY_OPTIONS = ["EASY", "MEDIUM", "HARD", "MULTIPLAYER"]

 

ROT_BTN_PIN = board.D0

ROT_A_PIN = board.D8

ROT_B_PIN = board.D9

 

LED_PIN = board.D1

NUM_LEDS = 1

 

SPEAKER_PIN = board.D10

 

# --------------------

# util

# --------------------

def map_range(x, in_min, in_max, out_min, out_max):

    if in_min == in_max:

        return out_min

    if x < in_min:

        x = in_min

    if x > in_max:

        x = in_max

    return out_min + (out_max - out_min) * (x - in_min) / (in_max - in_min)

 

# --------------------

# hardware init

# --------------------

displayio.release_displays()

i2c = busio.I2C(board.SCL, board.SDA)

 

display_bus = i2cdisplaybus.I2CDisplayBus(i2c, device_address=0x3C)

display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=SCREEN_WIDTH, height=SCREEN_HEIGHT)

 

accelerometer = adafruit_adxl34x.ADXL345(i2c)

accelerometer.range = adafruit_adxl34x.Range.RANGE_2_G

 

rot_btn = digitalio.DigitalInOut(ROT_BTN_PIN)

rot_btn.switch_to_input(pull=digitalio.Pull.UP)

last_btn_state = rot_btn.value

 

rot_a = digitalio.DigitalInOut(ROT_A_PIN)

rot_a.switch_to_input(pull=digitalio.Pull.UP)

rot_b = digitalio.DigitalInOut(ROT_B_PIN)

rot_b.switch_to_input(pull=digitalio.Pull.UP)

rot_last_state = rot_a.value

 

pixels = neopixel.NeoPixel(LED_PIN, NUM_LEDS, brightness=0.3, auto_write=True)

 

# Speaker setup

speaker = pwmio.PWMOut(SPEAKER_PIN, variable_frequency=True)

speaker.duty_cycle = 0  # Start silent

 

# --------------------

# Sound Effects

# --------------------

def play_tone(frequency, duration, duty_cycle=32768):

    """Play a tone at given frequency for duration in seconds"""

    if frequency > 0:

        speaker.frequency = frequency

        speaker.duty_cycle = duty_cycle

    time.sleep(duration)

    speaker.duty_cycle = 0

    time.sleep(0.01)

 

def startup_sound():

    """Ascending cheerful startup tune"""

    play_tone(523, 0.1)  # C5

    play_tone(659, 0.1)  # E5

    play_tone(784, 0.15) # G5

    play_tone(1047, 0.2) # C6

 

def game_start_sound():

    """Quick energetic game start"""

    play_tone(880, 0.08)  # A5

    play_tone(1047, 0.08) # C6

    play_tone(1319, 0.12) # E6

 

def game_over_sound():

    """Descending sad game over tune"""

    play_tone(659, 0.15)  # E5

    play_tone(587, 0.15)  # D5

    play_tone(523, 0.15)  # C5

    play_tone(392, 0.3)   # G4

 

def win_sound():

    """Victory fanfare"""

    play_tone(784, 0.1)   # G5

    play_tone(988, 0.1)   # B5

    play_tone(1175, 0.1)  # D6

    play_tone(1568, 0.3)  # G6

 

splash = displayio.Group()

display.root_group = splash

 

# --------------------

# UI

# --------------------

title_label = label.Label(terminalio.FONT, text="", color=0xFFFF00)

title_label.anchor_point = (0.5, 0.0)

title_label.anchored_position = (SCREEN_WIDTH // 2, 0)

splash.append(title_label)

 

level_label = label.Label(terminalio.FONT, text="", color=0xFFFF00)

level_label.anchored_position = (0, 0)

level_label.anchor_point = (0.0, 0.0)

splash.append(level_label)

 

timer_label = label.Label(terminalio.FONT, text="", color=0xFFFFFF)

timer_label.anchor_point = (0.0, 0.0)

timer_label.anchored_position = (0, 10)

splash.append(timer_label)

 

lives_label = label.Label(terminalio.FONT, text="", color=0xFFFFFF)

lives_label.anchor_point = (1.0, 0.0)

lives_label.anchored_position = (SCREEN_WIDTH - 2, 0)

splash.append(lives_label)

 

score_label = label.Label(terminalio.FONT, text="", color=0xFFFFFF)

score_label.anchor_point = (1.0, 0.0)

score_label.anchored_position = (SCREEN_WIDTH - 2, 10)

splash.append(score_label)

 

# High score display labels

hs_title_label = label.Label(terminalio.FONT, text="", color=0xFFFF00)

hs_title_label.anchor_point = (0.5, 0.0)

hs_title_label.anchored_position = (SCREEN_WIDTH // 2, 5)

splash.append(hs_title_label)

 

hs_line1_label = label.Label(terminalio.FONT, text="", color=0xFFFFFF)

hs_line1_label.anchor_point = (0.5, 0.0)

hs_line1_label.anchored_position = (SCREEN_WIDTH // 2, 20)

splash.append(hs_line1_label)

 

hs_line2_label = label.Label(terminalio.FONT, text="", color=0xFFFFFF)

hs_line2_label.anchor_point = (0.5, 0.0)

hs_line2_label.anchored_position = (SCREEN_WIDTH // 2, 30)

splash.append(hs_line2_label)

 

hs_line3_label = label.Label(terminalio.FONT, text="", color=0xFFFFFF)

hs_line3_label.anchor_point = (0.5, 0.0)

hs_line3_label.anchored_position = (SCREEN_WIDTH // 2, 40)

splash.append(hs_line3_label)

 

hs_prompt_label = label.Label(terminalio.FONT, text="", color=0x00FF00)

hs_prompt_label.anchor_point = (0.5, 0.0)

hs_prompt_label.anchored_position = (SCREEN_WIDTH // 2, 52)

splash.append(hs_prompt_label)

 

message_label = label.Label(terminalio.FONT, text="", color=0xFFFFFF)

message_label.anchor_point = (0.5, 0.5)

message_label.anchored_position = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

splash.append(message_label)

 

# --------------------

# Claw

# --------------------

start_claw_x = (SCREEN_WIDTH - CLAW_WIDTH) // 2

 

claw_line1 = label.Label(terminalio.FONT, text="   ||", color=0xFFFFFF, x=start_claw_x, y=CLAW_Y1_BASE)

claw_line2 = label.Label(terminalio.FONT, text="  ====", color=0xFFFFFF, x=start_claw_x, y=CLAW_Y2_BASE)

claw_line3 = label.Label(terminalio.FONT, text="  |  |", color=0xFFFFFF, x=start_claw_x, y=CLAW_Y3_BASE)

splash.append(claw_line1)

splash.append(claw_line2)

splash.append(claw_line3)

 

def set_claw_y(offset):

    claw_line1.y = CLAW_Y1_BASE + offset

    claw_line2.y = CLAW_Y2_BASE + offset

    claw_line3.y = CLAW_Y3_BASE + offset

 

# --------------------

# Player

# --------------------

player_x = SCREEN_WIDTH // 2

player_label = label.Label(terminalio.FONT, text="*", color=0xFFFFFF, x=player_x, y=PLAYER_Y)

splash.append(player_label)

 

# --------------------

# MULTIPLAYER UART

# --------------------

uart = None

multiplayer_active = False

opponent_aim_raw = 0.0

fire_flag = False

last_player_x = 0

 

def init_multiplayer_uart():

    global uart, multiplayer_active, opponent_aim_raw, fire_flag

    try:

        uart = busio.UART(tx=board.D6, rx=board.D7, baudrate=115200, timeout=0.01)

        multiplayer_active = True

        opponent_aim_raw = 0.0

        fire_flag = False

        print("Multiplayer UART initialized.")

    except Exception as e:

        uart = None

        multiplayer_active = False

        print("Failed to init UART:", e)

 

def deinit_multiplayer_uart():

    global uart, multiplayer_active

    try:

        if uart:

            uart.deinit()

    except Exception:

        pass

    uart = None

    multiplayer_active = False

 

def process_uart():

    """Receive claw position and fire commands"""

    global opponent_aim_raw, fire_flag

    if not multiplayer_active or not uart:

        return

    # Read all available data to get latest state

    while True:

        try:

            data = uart.readline()

        except Exception:

            return

        if not data:

            break

        try:

            msg = data.decode().strip()

        except Exception:

            continue

 

        if msg.startswith("AIM:"):

            try:

                val_str = msg.split(":",1)[1]

                val = float(val_str)

                opponent_aim_raw = val

            except Exception:

                pass

        elif msg == "FIRE:1":

            fire_flag = True

 

def send_player_position():

    """Send our player position to shooter"""

    global last_player_x

    if not multiplayer_active or not uart:

        return

    # Only send if changed

    if abs(player_x - last_player_x) >= 1:

        try:

            msg = f"P:{player_x}\n"

            uart.write(msg.encode())

            last_player_x = player_x

        except Exception:

            pass

 

# --------------------

# Game state

# --------------------

in_menu = True

menu_index = 0

difficulty = None

current_level_index = 0

level_time_target = LEVEL_DATA[0]

level_start_time = 0.0

game_state = "PLAYING"

lives = 3

score = 0  # Track successful dodges

splash_screen_shown = False  # Track if splash screen has played

 

claw_y_offset = CLAW_RESET_Y

claw_speed = INITIAL_CLAW_SPEED

claw_has_hit = False

last_hit_time = 0.0  # Cooldown timer to prevent rapid hits

HIT_COOLDOWN = 0.5  # Minimum time between hits in seconds

 

# --------------------

# High Score System

# --------------------

HIGH_SCORE_FILE = "/high_scores.txt"

high_scores = []  # List of tuples: (initials, score)

entering_initials = False

initial_index = 0  # Which letter we're editing (0, 1, or 2)

current_initials = ['A', 'A', 'A']

 

def load_high_scores():

    """Load high scores from flash memory"""

    global high_scores

    try:

        with open(HIGH_SCORE_FILE, 'r') as f:

            high_scores = []

            for line in f:

                line = line.strip()

                if line:

                    parts = line.split(',')

                    if len(parts) == 2:

                        initials = parts[0]

                        score_val = int(parts[1])

                        high_scores.append((initials, score_val))

        # Sort by score descending

        high_scores.sort(key=lambda x: x[1], reverse=True)

        # Keep only top 3

        high_scores = high_scores[:3]

    except:

        # File doesn't exist or error reading, start with defaults

        high_scores = [("AAA", 0), ("AAA", 0), ("AAA", 0)]

 

def save_high_scores():

    """Save high scores to flash memory"""

    try:

        # Remount filesystem as writable

        storage.remount("/", False)

        with open(HIGH_SCORE_FILE, 'w') as f:

            for initials, score_val in high_scores:

                f.write(f"{initials},{score_val}\n")

        # Remount as read-only

        storage.remount("/", True)

    except Exception as e:

        print("Error saving high scores:", e)

 

def is_high_score(score_val):

    """Check if score qualifies for high score board"""

    if len(high_scores) < 3:

        return True

    return score_val > high_scores[-1][1]

 

def add_high_score(initials, score_val):

    """Add a new high score and save"""

    global high_scores

    high_scores.append((initials, score_val))

    high_scores.sort(key=lambda x: x[1], reverse=True)

    high_scores = high_scores[:3]

    save_high_scores()

 

# Load high scores at startup

load_high_scores()

 

# --------------------

# Health LEDs

# --------------------

def update_health_bar():

    for i in range(NUM_LEDS):

        if i < lives:

            pixels[i] = (0, 255, 0)

        else:

            pixels[i] = (0, 0, 255)

 

def clear_health_bar():

    for i in range(NUM_LEDS):

        pixels[i] = (255, 0, 0)

 

# --------------------

# Game start functions

# --------------------

def reset_claw_spawn(random_x=True):

    global claw_y_offset, claw_has_hit

    claw_y_offset = CLAW_RESET_Y

    claw_has_hit = False

    if random_x:

        # Spawn across full width - no safe corners!

        # Allow claw to spawn from -10 to screen width, so grabbers can reach edges

        x = random.randint(-10, SCREEN_WIDTH - CLAW_WIDTH + 10)

    else:

        x = (SCREEN_WIDTH - CLAW_WIDTH) // 2

    claw_line1.x = x

    claw_line2.x = x

    claw_line3.x = x

 

def start_easy():

    global difficulty, current_level_index, level_start_time, game_state, lives, claw_speed, score

    difficulty = "EASY"

    current_level_index = 0

    level_start_time = time.monotonic()

    game_state = "PLAYING"

    lives = 3

    score = 0

    title_label.text = "EASY"

    reset_claw_spawn()

    claw_speed = INITIAL_CLAW_SPEED

    deinit_multiplayer_uart()

    game_start_sound()

 

def start_medium():

    global difficulty, current_level_index, level_start_time, game_state, lives, claw_speed, score

    difficulty = "MEDIUM"

    current_level_index = 0

    level_start_time = time.monotonic()

    game_state = "PLAYING"

    lives = 3

    score = 0

    title_label.text = "MEDIUM"

    reset_claw_spawn()

    claw_speed = INITIAL_CLAW_SPEED + 0.4

    deinit_multiplayer_uart()

    game_start_sound()

 

def start_hard():

    global difficulty, current_level_index, level_start_time, game_state, lives, claw_speed, score

    difficulty = "HARD"

    current_level_index = 0

    level_start_time = time.monotonic()

    game_state = "PLAYING"

    lives = 3

    score = 0

    title_label.text = "HARD"

    reset_claw_spawn()

    claw_speed = INITIAL_CLAW_SPEED + 0.8

    deinit_multiplayer_uart()

    game_start_sound()

 

def start_multiplayer():

    global difficulty, current_level_index, level_start_time, game_state, lives

    global claw_y_offset, score

    difficulty = "MULTIPLAYER"

    current_level_index = 0

    level_time_target = 60.0  # 60 second rounds

    level_start_time = time.monotonic()

    game_state = "PLAYING"

    lives = 3

    score = 0

    title_label.text = "MULTI"

    claw_y_offset = CLAW_RESET_Y

    set_claw_y(int(claw_y_offset))

    # Center claw initially

    x = (SCREEN_WIDTH - CLAW_WIDTH) // 2

    claw_line1.x = x

    claw_line2.x = x

    claw_line3.x = x

    init_multiplayer_uart()

    game_start_sound()

 

def start_level_same_difficulty():

    global level_start_time, claw_speed, current_level_index

    level_start_time = time.monotonic()

    if difficulty != "MULTIPLAYER":

        reset_claw_spawn()

        claw_speed = INITIAL_CLAW_SPEED + CLAW_SPEED_STEP * current_level_index

 

# --------------------

# Animated Splash Screen

# --------------------

def animated_splash_screen():

    """Show animated splash screen with falling claw animation"""

    global splash_screen_shown

    

    if splash_screen_shown:

        return

    

    splash_screen_shown = True

    

    # Create splash labels

    game_title = label.Label(terminalio.FONT, text="DODGE GAME", color=0xFFFF00)

    game_title.anchor_point = (0.5, 0.5)

    game_title.anchored_position = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 10)

    splash.append(game_title)

    

    subtitle = label.Label(terminalio.FONT, text="v1.0", color=0xFFFFFF)

    subtitle.anchor_point = (0.5, 0.5)

    subtitle.anchored_position = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 5)

    splash.append(subtitle)

    

    # Create animated claw for splash

    splash_claw = label.Label(terminalio.FONT, text="  |  |", color=0xFFFFFF)

    splash_claw.anchor_point = (0.5, 0.0)

    splash_claw.anchored_position = (SCREEN_WIDTH // 2, 0)

    splash.append(splash_claw)

    

    # Animate claw dropping all the way to the bottom

    for y in range(0, SCREEN_HEIGHT, 2):

        splash_claw.y = y

        time.sleep(0.025)

    

    # Quick rise back up off screen

    for y in range(SCREEN_HEIGHT, -15, -4):

        splash_claw.y = y

        time.sleep(0.015)

    

    # Flash the title

    for _ in range(3):

        game_title.color = 0x00FF00

        time.sleep(0.15)

        game_title.color = 0xFFFF00

        time.sleep(0.15)

    

    time.sleep(0.5)

    

    # Remove splash elements

    splash.remove(game_title)

    splash.remove(subtitle)

    splash.remove(splash_claw)



# --------------------

# Calibration

# --------------------

def calibrate_accelerometer():

    """Show accelerometer values for calibration"""

    title_label.text = "CALIBRATE"

    message_label.text = "Tilt to test"

    

    calib_start = time.monotonic()

    calib_duration = 5.0  # Show calibration for 5 seconds

    

    # Create temporary label for showing accel values

    accel_label = label.Label(terminalio.FONT, text="", color=0xFFFFFF)

    accel_label.anchor_point = (0.5, 0.5)

    accel_label.anchored_position = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 15)

    splash.append(accel_label)

    

    min_x, max_x = 0.0, 0.0

    

    while time.monotonic() - calib_start < calib_duration:

        try:

            ax, ay, az = accelerometer.acceleration

            if ax < min_x:

                min_x = ax

            if ax > max_x:

                max_x = ax

            accel_label.text = f"X:{ax:.1f}\nMin:{min_x:.1f} Max:{max_x:.1f}"

        except:

            accel_label.text = "Error reading"

        

        time.sleep(0.1)

    

    # Remove calibration label

    splash.remove(accel_label)

    message_label.text = ""



# Show animated splash screen on first boot

animated_splash_screen()



# Play startup sound

startup_sound()



# Run calibration at startup

calibrate_accelerometer()



# --------------------

# Menu

# --------------------

def show_menu():

    global in_menu

    in_menu = True

    clear_health_bar()

    title_label.text = "MENU"

    message_label.text = f"< {DIFFICULTY_OPTIONS[menu_index]} >"

    reset_claw_spawn(random_x=False)

    set_claw_y(CLAW_RESET_Y)

    # Hide claw completely off-screen in menu

    claw_line1.y = -100

    claw_line2.y = -100

    claw_line3.y = -100

    # Clear high score display

    hs_title_label.text = ""

    hs_line1_label.text = ""

    hs_line2_label.text = ""

    hs_line3_label.text = ""

    hs_prompt_label.text = ""

    deinit_multiplayer_uart()

 

def show_high_scores():

    """Display the high score board"""

    # Hide game elements

    title_label.text = ""

    level_label.text = ""

    timer_label.text = ""

    lives_label.text = ""

    score_label.text = ""

    message_label.text = ""

    

    # Hide claw

    claw_line1.y = -100

    claw_line2.y = -100

    claw_line3.y = -100

    

    # Show high scores

    hs_title_label.text = "HIGH SCORES"

    if len(high_scores) > 0:

        hs_line1_label.text = f"1. {high_scores[0][0]} - {high_scores[0][1]}"

    if len(high_scores) > 1:

        hs_line2_label.text = f"2. {high_scores[1][0]} - {high_scores[1][1]}"

    if len(high_scores) > 2:

        hs_line3_label.text = f"3. {high_scores[2][0]} - {high_scores[2][1]}"

    

    hs_prompt_label.text = "Press to continue"

 

def show_initial_entry():

    """Display initial entry screen"""

    global entering_initials, initial_index, current_initials

    entering_initials = True

    initial_index = 0

    current_initials = ['A', 'A', 'A']

    

    # Hide game elements

    title_label.text = ""

    level_label.text = ""

    timer_label.text = ""

    lives_label.text = ""

    score_label.text = ""

    message_label.text = ""

    

    # Hide claw

    claw_line1.y = -100

    claw_line2.y = -100

    claw_line3.y = -100

    

    hs_title_label.text = "NEW HIGH SCORE!"

    update_initial_display()

 

def update_initial_display():

    """Update the display showing current initials being entered"""

    # Show initials with cursor

    initial_str = ""

    for i in range(3):

        if i == initial_index:

            initial_str += f"[{current_initials[i]}]"

        else:

            initial_str += f" {current_initials[i]} "

    

    hs_line1_label.text = ""

    hs_line2_label.text = initial_str

    hs_line3_label.text = ""

    hs_prompt_label.text = "Rotate:Change Press:Next"

 

show_menu()

 

# --------------------

# Collision

# --------------------

def check_collision():
    """Check collision with the claw grabbers - hits if touching either | or caught between them"""
    # The claw text is "  |  |" - the | symbols are at character positions 2 and 5
    claw_base_x = claw_line3.x  # Use line3's x position directly
    
    # Calculate pixel positions of the two grabber lines (| symbols)
    # Each character is 6 pixels wide in terminalio.FONT
    left_grabber_x = claw_base_x + (2 * 6) + 2  # Left edge of first | symbol
    right_grabber_x = claw_base_x + (5 * 6) + 2  # Left edge of second | symbol
    grabber_width = 2  # The | symbol is only 2 pixels wide
    
    player_center = player_x + PLAYER_WIDTH // 2
    player_radius = 3  # Player hitbox radius
 
    # Only the bottom claw line (line3) can hit you
    claw_bottom = claw_line3.y
 
    # Only trigger when the bottom part is at or past the player level
    if claw_bottom >= PLAYER_Y - 2 and claw_bottom <= PLAYER_Y + 4:
        # Check if player hits left grabber
        left_hit = (player_center >= left_grabber_x - player_radius and 
                   player_center <= left_grabber_x + grabber_width + player_radius)
        # Check if player hits right grabber
        right_hit = (player_center >= right_grabber_x - player_radius and 
                    player_center <= right_grabber_x + grabber_width + player_radius)
        # Check if player is caught BETWEEN the grabbers
        caught_between = (player_center > left_grabber_x + grabber_width and 
                         player_center < right_grabber_x)
        
        if left_hit or right_hit or caught_between:
            return True
    return False

 

# --------------------

# Multiplayer claw drop

# --------------------

def drop_claw_multiplayer():

    global lives, game_state, claw_y_offset, last_hit_time

    if game_state != "PLAYING":

        return

 

    hit_detected = False

    current_time = time.monotonic()

 

    # Drop animation

    for step in range(DROP_STEPS + 1):

        offset = step * DROP_STEP_PIXELS

        claw_y_offset = offset

        set_claw_y(offset)

 

        # Check collision during drop (with cooldown)

        if check_collision() and not hit_detected and (current_time - last_hit_time) > HIT_COOLDOWN:

            lives -= 1

            update_health_bar()

            hit_detected = True

            last_hit_time = time.monotonic()

            if lives <= 0:

                game_state = "GAME_OVER"

                message_label.text = f"GAME OVER\nScore: {score}"

                game_over_sound()

 

        time.sleep(0.03)

 

    time.sleep(0.15)

 

    # Rise back up (no collision checking on the way up)

    for step in range(DROP_STEPS, -1, -1):

        offset = step * DROP_STEP_PIXELS

        claw_y_offset = offset

        set_claw_y(offset)

        time.sleep(0.03)

 

    claw_y_offset = CLAW_RESET_Y
    
    # Small delay to prevent immediate re-triggering
    time.sleep(0.1)

 

# --------------------

# Main loop

# --------------------

while True:

    current_btn = rot_btn.value

    button_pressed = last_btn_state and (not current_btn)

    last_btn_state = current_btn

 

    current_rot_a = rot_a.value

    if in_menu and (current_rot_a != rot_last_state):

        if not current_rot_a:

            if rot_b.value:

                menu_index += 1

            else:

                menu_index -= 1

            menu_index %= len(DIFFICULTY_OPTIONS)

            message_label.text = f"< {DIFFICULTY_OPTIONS[menu_index]} >"

        rot_last_state = current_rot_a

 

    # MENU SELECTION

    if in_menu:

        if button_pressed:

            sel = DIFFICULTY_OPTIONS[menu_index]

            in_menu = False

            if sel == "EASY":

                start_easy()

            elif sel == "MEDIUM":

                start_medium()

            elif sel == "HARD":

                start_hard()

            elif sel == "MULTIPLAYER":

                start_multiplayer()

            update_health_bar()

            message_label.text = ""

        time.sleep(0.02)

        continue

 

    # Process UART if multiplayer

    if multiplayer_active:

        process_uart()

 

    # TIMER UPDATE

    now = time.monotonic()

    remaining = level_time_target - (now - level_start_time)

    if remaining < 0:

        remaining = 0

    level_label.text = f"Lv{current_level_index + 1}"

    lives_label.text = f"L{lives}"

    timer_label.text = f"T:{int(remaining)}s"

    score_label.text = f"S:{score}"

 

    # PLAYER MOVEMENT (always local control)

    try:

        ax, ay, az = accelerometer.acceleration

    except:

        ax = 0

 

    move_speed = map_range(ax, ACCEL_MIN, ACCEL_MAX, -10, 10)

    player_x += int(move_speed)

 

    if player_x < 0:

        player_x = 0

    if player_x > SCREEN_WIDTH - PLAYER_WIDTH:

        player_x = SCREEN_WIDTH - PLAYER_WIDTH

    player_label.x = int(player_x)

 

    # Send player position in multiplayer

    if multiplayer_active:

        send_player_position()

 

    # CLAW CONTROL

    if difficulty == "MULTIPLAYER" and multiplayer_active:

        # Opponent controls claw position

        try:

            claw_x = int(map_range(opponent_aim_raw, ACCEL_MIN, ACCEL_MAX, 0, SCREEN_WIDTH - CLAW_WIDTH))

        except Exception:

            claw_x = claw_line1.x

        claw_line1.x = claw_x

        claw_line2.x = claw_x

        claw_line3.x = claw_x

 

        # Handle fire command

        if fire_flag and game_state == "PLAYING":

            drop_claw_multiplayer()

            fire_flag = False

 

    elif game_state == "PLAYING":

        # Single player - automatic claw

        claw_y_offset += claw_speed

        set_claw_y(int(claw_y_offset))

 

        if claw_y_offset > (PLAYER_Y + 8):

            # Successfully dodged! Increment score only if we didn't get hit

            if not claw_has_hit:

                score += 1

            reset_claw_spawn(random_x=True)

 

        # Only check collision once when claw reaches player, prevent multiple hits

        current_time = time.monotonic()

        if not claw_has_hit and check_collision() and (current_time - last_hit_time) > HIT_COOLDOWN:

            lives -= 1

            update_health_bar()

            claw_has_hit = True

            last_hit_time = current_time

            if lives <= 0:

                game_state = "GAME_OVER"

                message_label.text = f"GAME OVER\nScore: {score}"

                game_over_sound()

 

    # LEVEL COMPLETE (not for multiplayer)

    if difficulty != "MULTIPLAYER" and game_state == "PLAYING" and remaining <= 0:

        if current_level_index < len(LEVEL_DATA)-1:

            current_level_index += 1

            level_time_target = LEVEL_DATA[current_level_index]

            start_level_same_difficulty()

        else:

            game_state = "WIN"

            message_label.text = f"YOU WIN!\nScore: {score}"

            win_sound()

    elif difficulty == "MULTIPLAYER" and game_state == "PLAYING" and remaining <= 0:

        game_state = "WIN"

        message_label.text = f"YOU SURVIVED!\nScore: {score}"

        win_sound()

 

    # HIGH SCORE AND MENU HANDLING

    if entering_initials:

        # Handle initial entry with rotary encoder

        current_rot_a = rot_a.value

        if current_rot_a != rot_last_state:

            if not current_rot_a:

                if rot_b.value:

                    # Rotate clockwise - next letter

                    ord_val = ord(current_initials[initial_index])

                    ord_val += 1

                    if ord_val > ord('Z'):

                        ord_val = ord('A')

                    current_initials[initial_index] = chr(ord_val)

                else:

                    # Rotate counter-clockwise - prev letter

                    ord_val = ord(current_initials[initial_index])

                    ord_val -= 1

                    if ord_val < ord('A'):

                        ord_val = ord('Z')

                    current_initials[initial_index] = chr(ord_val)

                update_initial_display()

            rot_last_state = current_rot_a

        

        # Button press moves to next initial or confirms

        if button_pressed:

            initial_index += 1

            if initial_index >= 3:

                # Done entering initials

                initials_str = ''.join(current_initials)

                add_high_score(initials_str, score)

                entering_initials = False

                game_state = "SHOW_HIGH_SCORES"

                show_high_scores()

            else:

                update_initial_display()

    

    elif game_state == "SHOW_HIGH_SCORES":

        # Showing high scores, press button to return to menu

        if button_pressed:

            show_menu()

            game_state = "PLAYING"

    

    elif game_state == "GAME_OVER" or game_state == "WIN":

        # Check if this is a high score

        if is_high_score(score):

            show_initial_entry()

        else:

            # Not a high score, show high score board

            game_state = "SHOW_HIGH_SCORES"

            show_high_scores()

 

    time.sleep(0.01)  # Faster loop for multiplayer