import time
import board
import busio
import displayio
import terminalio
from adafruit_display_text import label
import wifi
import json
from adafruit_datetime import datetime, timedelta
import rtc
import socketpool
import adafruit_ntp
import adafruit_displayio_ssd1306
import microcontroller

# Setup OLED display
displayio.release_displays()
i2c = busio.I2C(scl=board.GP1, sda=board.GP0)
display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
WIDTH = 128
HEIGHT = 64
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)

# Function to display messages on the OLED screen
def display_message(lines):
    splash = displayio.Group()
    y = 4
    for line in lines:
        text_area = label.Label(terminalio.FONT, text=line, color=0xFFFFFF, x=0, y=y)
        splash.append(text_area)
        y += 11
    display.root_group = splash

# Function to display the countdown on the OLED screen
def display_countdown(days_remaining, target_label):
    splash = displayio.Group()

    # Title text
    title_text = f"Days until {target_label}"
    title_area = label.Label(terminalio.FONT, text=title_text, color=0xFFFFFF, scale=1)
    title_area.x = (WIDTH - title_area.bounding_box[2]) // 2
    title_area.y = 5
    splash.append(title_area)

    # Countdown number (large font)
    days_text = str(days_remaining)
    days_area = label.Label(terminalio.FONT, text=days_text, color=0xFFFFFF, scale=6)

    # Adjust position based on the number of digits
    if len(days_text) == 1:  # Single digit
        days_area.x = 50
        days_area.y = 38
    elif len(days_text) == 2:  # Two digits
        days_area.x = 30
        days_area.y = 38
    elif len(days_text) == 3:  # Three digits
        days_area.x = 10
        days_area.y = 38

    splash.append(days_area)

    display.root_group = splash

# Function to load configuration
def load_configuration():
    try:
        with open("/config.json", "r") as f:
            config = json.load(f)
        # Set default values for new keys if they are missing
        if "target_date" not in config:
            config["target_date"] = "12-24"  # Default to December 24th
        if "target_label" not in config:
            config["target_label"] = "Event"  # Default label
        return config
    except OSError as e:
        print("Configuration not found. Starting with default configuration.")
        return None

# Function to synchronize time
def synchronize_time(timezone_offset):
    try:
        pool = socketpool.SocketPool(wifi.radio)
        ntp = adafruit_ntp.NTP(pool, tz_offset=timezone_offset)
        rtc.RTC().datetime = ntp.datetime
        print("Time synchronized!")
    except Exception as e:
        print("Failed to synchronize time:", e)
        display_message(["Time Sync Error!", "Rebooting..."])
        time.sleep(5)
        microcontroller.reset()

# Function to calculate days remaining until the target date
def calculate_days_remaining(target_month, target_day):
    now = datetime.now()
    today = datetime(now.year, now.month, now.day)

    # Determine the target year
    if (now.month > target_month) or (now.month == target_month and now.day > target_day):
        target_year = now.year + 1
    else:
        target_year = now.year

    target_date = datetime(target_year, target_month, target_day)
    delta = target_date - today
    return delta.days

# Main function
def main():
    print("Starting main function...")

    config = load_configuration()
    if config is None:
        print("No configuration found. Please set up the device.")
        display_message(["No Config Found!", "Rebooting..."])
        time.sleep(3)
        microcontroller.reset()

    # Connect to Wi-Fi
    try:
        wifi.radio.connect(config["ssid"], config["password"])
        print("Connected to Wi-Fi!")
        display_message(["Wi-Fi Connected!", "Syncing Time..."])
        time.sleep(1)
    except Exception as e:
        print("Failed to connect to Wi-Fi:", e)
        display_message(["Wi-Fi Error!", "Rebooting..."])
        time.sleep(5)
        microcontroller.reset()

    # Synchronize time
    synchronize_time(config.get("timezone", 0))

    # Initialize countdown display
    target_date = config["target_date"]
    target_label = config["target_label"]
    target_month, target_day = map(int, target_date.split("-"))

    print(f"Countdown target set to {target_date} for {target_label}.")
    last_days_remaining = None

    while True:
        # Calculate days remaining
        days_remaining = calculate_days_remaining(target_month, target_day)

        if days_remaining != last_days_remaining:
            display_countdown(days_remaining, target_label)
            print(f"Days remaining until {target_label}: {days_remaining}")
            last_days_remaining = days_remaining

        # Sleep until the next day
        now = datetime.now()
        next_midnight = datetime(now.year, now.month, now.day) + timedelta(days=1)
        sleep_seconds = (next_midnight - now).total_seconds()
        time.sleep(sleep_seconds)

if __name__ == "__main__":
    main()
