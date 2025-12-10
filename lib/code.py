# dodge_game.py
# DODGE game — player controls the dot (tilt) and dodges a falling claw (enemy).
# NO MUSIC, NO VIBRATION — cleaned version.

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

ACCEL_MIN = -9.0
ACCEL_MAX = 9.0

PLAYER_WIDTH = 8
PLAYER_Y = 52

LEVEL_DATA = [
    15.0, 14.0, 13.0, 12.0, 11.0,
    10.0, 9.0, 8.0, 7.0, 6.0
]

DIFFICULTY_OPTIONS = ["EASY", "MEDIUM", "HARD"]

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
    global claw_y_offset
    claw_y_offset = CLAW_RESET_Y
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

def start_level_same_difficulty():
    global level_start_time, claw_speed, current_level_index
    level_start_time = time.monotonic()
    reset_claw_spawn()
    claw_speed = INITIAL_CLAW_SPEED + CLAW_SPEED_STEP * current_level_index

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

show_menu()

# --------------------
# Collision
# --------------------
def check_collision():
    claw_left = claw_line1.x
    claw_right = claw_left + CLAW_WIDTH
    player_center = player_x + PLAYER_WIDTH // 2
    claw_bottom = CLAW_Y3_BASE + int(claw_y_offset)

    if claw_bottom >= PLAYER_Y - 2:
        if claw_left <= player_center <= claw_right:
            return True
    return False

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
            update_health_bar()
            message_label.text = ""
        time.sleep(0.02)
        continue

    # TIMER UPDATE
    now = time.monotonic()
    remaining = level_time_target - (now - level_start_time)
    if remaining < 0:
        remaining = 0
    #timer_label.text = f"{remaining:4.1f}"
    level_label.text = f"Lv{current_level_index}"
    lives_label.text = f"L{lives}"

    # PLAYER MOVEMENT
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

    # CLAW MOVEMENT
    if game_state == "PLAYING":
        claw_y_offset += claw_speed
        set_claw_y(int(claw_y_offset))

        if claw_y_offset > (PLAYER_Y + 8):
            reset_claw_spawn(random_x=True)

        if check_collision():
            lives -= 1
            update_health_bar()
            reset_claw_spawn(random_x=True)
            if lives <= 0:
                game_state = "GAME_OVER"
                message_label.text = "GAME OVER"

    # LEVEL COMPLETE
    if game_state == "PLAYING" and remaining <= 0:
        if current_level_index < len(LEVEL_DATA)-1:
            current_level_index += 1
            level_time_target = LEVEL_DATA[current_level_index]
            start_level_same_difficulty()
        else:
            game_state = "WIN"
            message_label.text = "YOU WIN!"

    # RETURN TO MENU
    if button_pressed and game_state in ("GAME_OVER", "WIN"):
        show_menu()

    time.sleep(0.02)
