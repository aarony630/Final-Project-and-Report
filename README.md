# Final-Project-and-Report
To design and implement an embedded powered 90s era style handheld electronic game

##Overview

This project is an interactive tilt-controlled game built using a Seeed Xiao ESP32,
an SSD1306 OLED display, a NeoPixel LED, a rotary encoder, and an ADXL345 accelerometer.
The objective of the game is for the player to control a small character (“*”) by tilting
the device left or right to dodge falling obstacles (the “claw”).
The game includes a menu system,
difficulty settings, levels, a timer, and a life system displayed through LEDs.

When the device starts, the game enters a menu mode.
The rotary encoder is used to scroll through three difficulty options:

EASY

MEDIUM

HARD

Pressing the encoder button starts the selected mode.
Each difficulty affects the speed of the falling claw.

Additional Hardware: Fan, Speaker

Thought process of my design 
For my game, I created a “Dodge the Bomb” concept where the player must tilt the device to avoid a falling object.
Originally, the Moving part is an egg, but I redesigned the theme so that the danger is now a bomb.
When the player fails to dodge,
the bomb “explodes,” causing the player to lose a life.
Because the entire game centers around avoiding an explosive,
I wanted the physical case to reflect that same theme.
This led to the idea of designing a grenade-shaped enclosure.
