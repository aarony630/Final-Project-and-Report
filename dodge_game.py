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
    15.0, 14.0, 13.0, 12.0, 11.0,
    10.0, 9.0, 8.0, 7.0, 6.0
]

DIFFICULTY_OPTIONS = ["EASY", "MEDIUM", "HARD", "MULTIPLAYER"]

ROT_BTN_PIN = board.D0
ROT_A_PIN = board.D8
ROT_B_PIN = board.D9

LED_PIN = board.D1
NUM_LEDS = 1

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
timer_label.anchored_position = (0, 10)
splash.append(timer_label)

lives_label = label.Label(terminalio.FONT, text="", color=0xFFFFFF)
lives_label.anchor_point = (1.0, 0.0)
lives_label.anchored_position = (SCREEN_WIDTH - 2, 0)
splash.append(lives_label)

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

claw_y_offset = CLAW_RESET_Y
claw_speed = INITIAL_CLAW_SPEED
claw_has_hit = False

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
        x = random.randint(0, SCREEN_WIDTH - CLAW_WIDTH)
    else:
        x = (SCREEN_WIDTH - CLAW_WIDTH) // 2
    claw_line1.x = x
    claw_line2.x = x
    claw_line3.x = x

def start_easy():
    global difficulty, current_level_index, level_start_time, game_state, lives, claw_speed
    difficulty = "EASY"
    current_level_index = 0
    level_start_time = time.monotonic()
    game_state = "PLAYING"
    lives = 3
    title_label.text = "EASY"
    reset_claw_spawn()
    claw_speed = INITIAL_CLAW_SPEED
    deinit_multiplayer_uart()

def start_medium():
    global difficulty, current_level_index, level_start_time, game_state, lives, claw_speed
    difficulty = "MEDIUM"
    current_level_index = 0
    level_start_time = time.monotonic()
    game_state = "PLAYING"
    lives = 3
    title_label.text = "MEDIUM"
    reset_claw_spawn()
    claw_speed = INITIAL_CLAW_SPEED + 0.4
    deinit_multiplayer_uart()

def start_hard():
    global difficulty, current_level_index, level_start_time, game_state, lives, claw_speed
    difficulty = "HARD"
    current_level_index = 0
    level_start_time = time.monotonic()
    game_state = "PLAYING"
    lives = 3
    title_label.text = "HARD"
    reset_claw_spawn()
    claw_speed = INITIAL_CLAW_SPEED + 0.8
    deinit_multiplayer_uart()

def start_multiplayer():
    global difficulty, current_level_index, level_start_time, game_state, lives
    global claw_y_offset
    difficulty = "MULTIPLAYER"
    current_level_index = 0
    level_time_target = 60.0  # 60 second rounds
    level_start_time = time.monotonic()
    game_state = "PLAYING"
    lives = 3
    title_label.text = "MULTI"
    claw_y_offset = CLAW_RESET_Y
    set_claw_y(int(claw_y_offset))
    # Center claw initially
    x = (SCREEN_WIDTH - CLAW_WIDTH) // 2
    claw_line1.x = x
    claw_line2.x = x
    claw_line3.x = x
    init_multiplayer_uart()

def start_level_same_difficulty():
    global level_start_time, claw_speed, current_level_index
    level_start_time = time.monotonic()
    if difficulty != "MULTIPLAYER":
        reset_claw_spawn()
        claw_speed = INITIAL_CLAW_SPEED + CLAW_SPEED_STEP * current_level_index

# --------------------
# Calibration
# --------------------
def calibrate_accelerometer():
    """Calibrate accelerometer by tilting device fully left and right"""
    global ACCEL_MIN, ACCEL_MAX

    title_label.text = "CALIBRATE"
    message_label.text = "Tilt L+R"

    # Create temporary label for showing accel values
    accel_label = label.Label(terminalio.FONT, text="", color=0xFFFFFF)
    accel_label.anchor_point = (0.5, 0.5)
    accel_label.anchored_position = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 10)
    splash.append(accel_label)

    calib_start = time.monotonic()
    calib_duration = 5.0  # 5 second calibration window

    min_x = 0.0
    max_x = 0.0

    while time.monotonic() - calib_start < calib_duration:
        try:
            ax, ay, az = accelerometer.acceleration
            if ax < min_x:
                min_x = ax
            if ax > max_x:
                max_x = ax

            remaining = calib_duration - (time.monotonic() - calib_start)
            accel_label.text = f"X:{ax:.1f}\n{min_x:.1f} to {max_x:.1f}\n{remaining:.1f}s"
        except:
            accel_label.text = "Error reading"

        time.sleep(0.1)

    # Apply calibration values
    if abs(max_x - min_x) > 1.0:  # Only apply if there was meaningful tilt
        ACCEL_MIN = min_x
        ACCEL_MAX = max_x
        message_label.text = "Calibrated!"
    else:
        message_label.text = "Not enough tilt"

    # Remove calibration label
    splash.remove(accel_label)
    time.sleep(1)
    message_label.text = ""

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
    deinit_multiplayer_uart()

# Run calibration at startup
calibrate_accelerometer()

show_menu()

# --------------------
# Collision
# --------------------
def check_collision():
    """Only check collision with the bottom grabbing part of the claw (line 3)"""
    claw_left = claw_line1.x
    claw_right = claw_left + CLAW_WIDTH
    player_center = player_x + PLAYER_WIDTH // 2

    # Only the bottom claw line (line3) can hit you
    claw_bottom = claw_line3.y

    # Only trigger when the bottom part is at or past the player level
    # Only count as a hit when the claw's bottom is at (or very near) the player's Y.
    # This avoids counting hits when the claw has already passed the player or is far above.
    vertical_tolerance = DROP_STEP_PIXELS if DROP_STEP_PIXELS > 0 else 1
    if abs(claw_bottom - PLAYER_Y) <= vertical_tolerance:
        if claw_left <= player_center <= claw_right:
            return True
    return False

# --------------------
# Multiplayer claw drop
# --------------------
def drop_claw_multiplayer():
    global lives, game_state, claw_y_offset
    if game_state != "PLAYING":
        return

    hit_detected = False

    # Drop animation
    for step in range(DROP_STEPS + 1):
        offset = step * DROP_STEP_PIXELS
        claw_y_offset = offset
        set_claw_y(offset)

        # Check collision during drop
        if check_collision() and not hit_detected:
            lives -= 1
            update_health_bar()
            hit_detected = True
            if lives <= 0:
                game_state = "GAME_OVER"
                message_label.text = "GAME OVER"

        time.sleep(0.03)

    time.sleep(0.15)

    # Rise back up
    for step in range(DROP_STEPS, -1, -1):
        offset = step * DROP_STEP_PIXELS
        claw_y_offset = offset
        set_claw_y(offset)
        time.sleep(0.03)

    claw_y_offset = CLAW_RESET_Y

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
    level_label.text = f"Lv{current_level_index}"
    lives_label.text = f"L{lives}"

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
            reset_claw_spawn(random_x=True)

        # Only check collision once when claw reaches player, prevent multiple hits
        if not claw_has_hit and check_collision():
            lives -= 1
            update_health_bar()
            claw_has_hit = True
            if lives <= 0:
                game_state = "GAME_OVER"
                message_label.text = "GAME OVER"

    # LEVEL COMPLETE (not for multiplayer)
    if difficulty != "MULTIPLAYER" and game_state == "PLAYING" and remaining <= 0:
        if current_level_index < len(LEVEL_DATA)-1:
            current_level_index += 1
            level_time_target = LEVEL_DATA[current_level_index]
            start_level_same_difficulty()
        else:
            game_state = "WIN"
            message_label.text = "YOU WIN!"
    elif difficulty == "MULTIPLAYER" and game_state == "PLAYING" and remaining <= 0:
        game_state = "WIN"
        message_label.text = "YOU SURVIVED!"

    # RETURN TO MENU
    if button_pressed and game_state in ("GAME_OVER", "WIN"):
        show_menu()

    time.sleep(0.01)  # Faster loop for multiplayer

