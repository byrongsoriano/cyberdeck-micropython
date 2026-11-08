# PACE x IEEE x RAS Make&Take CyberDeck code in micropython

This repository contains `main_v8_stopwatch.py`, a MicroPython-based minimalist operating system and multi-app launcher designed for microcontrollers like the Raspberry Pi Pico 2. It features a custom ST7735 display driver, a retro-synthwave graphical interface, and a suite of built-in games and utilities.

## Features

* **Custom ST7735 Display Driver**: Optimized framebuf-based driver for 160x128 pixel SPI displays.


* **Retro UI & Splash Screen**: Boot animation featuring a synthwave-style sun, grid, and loading bar.


* **Dynamic Menu System**: Animated gradient selections, pulsing highlights, and custom icons for app navigation.


* **Audio Feedback**: PWM-based buzzer integration for UI navigation sounds, game effects (lasers, jumps, explosions), and startup chimes.


* **Included Applications**:
* **Flappy Bird**: An endless runner with parallax scrolling, gravity physics, collision detection, and high-score tracking.


* **Space Invaders**: A retro arcade shooter featuring enemy movement logic, particle explosion effects, and starry backgrounds.


* **Calculator**: A fully functional math utility supporting basic arithmetic and floating-point evaluation.


* **Stopwatch**: A precise timer tracking minutes, seconds, and milliseconds with start/stop/reset functionality.





## Hardware Configuration

This project is configured for a standard SPI setup. The pinout is defined as follows:

| Component | Pin Function | GPIO Pin |
| --- | --- | --- |
| **Display (ST7735)** | SCK (Clock) | 18


| **MOSI (Data)** | 19
| --- | --- | --- |

| **CS (Chip Select)** | 17
| --- | --- | --- |
| **DC (Data/Command)** | 16
| --- | --- | --- |

| **RST (Reset)** | 20
| --- | --- | --- |
 
| **Inputs** | NAV Button | 14 (Pull-up)
| --- | --- | --- |

| **SELECT Button** | 12 (Pull-up)
| --- | --- | --- |
 
| **Audio** | Buzzer (PWM) | 22 (Active Low)
| --- | --- | --- |
 

## Installation & Usage

1. Flash your microcontroller with the latest MicroPython firmware.
2. Upload `main_v8_stopwatch.py` to the root directory of your device.


3. Rename the file to `main.py` if you want the OS to boot automatically on startup.
4. **Navigation**: Press the **NAV** button (GPIO 14) to cycle through the menu and interface options.


5. **Selection**: Press the **SELECT** button (GPIO 12) to launch apps, interact with tools, or fire weapons in games.



## Technical Details

The codebase is written in standard MicroPython and relies heavily on the `framebuf` library for fast memory-buffered graphics. It utilizes custom dictionary-based sprite definitions and mathematical generation for procedural UI elements like sine-wave animations and gradient palettes. Garbage collection (`gc.collect()`) is aggressively managed throughout the codebase to ensure stable execution in memory-constrained environments.

