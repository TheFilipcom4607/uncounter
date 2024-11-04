import time
import board
import busio
import digitalio
import storage
import displayio
import terminalio
from adafruit_display_text import label
import wifi
import socketpool
import adafruit_ntp
import rtc
import json
from adafruit_datetime import datetime, timedelta
import adafruit_displayio_ssd1306
import microcontroller
import ssl
from adafruit_httpserver import Server, Request, Response, MIMETypes
import os
import random

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
    display.root_group = splash
    y = 4
    for line in lines:
        text_area = label.Label(terminalio.FONT, text=line, color=0xFFFFFF, x=0, y=y)
        splash.append(text_area)
        y += 11  # Adjust line spacing as needed

def check_for_safe_mode():
    pin = digitalio.DigitalInOut(board.GP14)  # Use GPIO14 (Pin 19)
    pin.switch_to_input(pull=digitalio.Pull.UP)
    if not pin.value:
        # Pin is bridged to GND, enter safe mode
        return True
    return False


if check_for_safe_mode():
    try:
        # Rename boot.py to but.py to disable it
        storage.remount("/", readonly=False)
        os.rename("/boot.py", "/but.py")
        # Display message on the screen
        display_message(["Safe mode entered.", "Rebooting now."])
        time.sleep(2)
        # Reboot the board
        microcontroller.reset()
    except Exception as e:
        # In case of an error, print it
        print("Failed to enter safe mode:", e)

# Function to display the countdown on the OLED screen
def display_countdown(days_remaining):
    splash = displayio.Group()
    display.root_group = splash

    title_text = "Days until Christmas"
    title_area = label.Label(terminalio.FONT, text=title_text, color=0xFFFFFF, scale=1)
    title_area.x = (WIDTH - title_area.bounding_box[2]) // 2
    title_area.y = 5
    splash.append(title_area)

    days_text = str(days_remaining)
    days_area = label.Label(terminalio.FONT, text=days_text, color=0xFFFFFF, scale=6)
    days_area.x = 35
    days_area.y = 40
    splash.append(days_area)

# Function to start access point mode with stabilization delay
def start_access_point():
    ap_ssid = "Christmas-Setup"
    ap_password = f"{random.randint(0, 99999999):08}"  # Ensure it's an 8-digit string
    wifi.radio.stop_station()  # Ensure station mode is off
    wifi.radio.start_ap(ssid=ap_ssid, password=ap_password)

    # Wait until we get an AP address assigned, with a stabilization delay
    max_wait = 10
    while not wifi.radio.ipv4_address_ap and max_wait > 0:
        time.sleep(1)
        max_wait -= 1

    # Adding extra stabilization time for AP mode to be fully ready
    time.sleep(2)

    ip = wifi.radio.ipv4_address_ap

    if ip:
        display_message([
            "Connect to Wi-Fi:",
            ap_ssid,
            "Password:",
            ap_password,
            "Visit:",
            f"{str(ip)}:8080"
        ])

    print("Access Point started")
    print("SSID:", ap_ssid)
    print("Password:", ap_password)
    print("IP address:", ip)

    return ip

# Improved version for running the server with a specific port
# Function to run the configuration web server
def run_configuration_server(ip):
    from adafruit_httpserver import Server, Request, Response, MIMETypes

    pool = socketpool.SocketPool(wifi.radio)
    server = Server(pool, "/static")

    @server.route("/", methods=["GET"])
    def index(request: Request):
        html = """
        <html>
        <head><title>Christmas Counter Configuration</title></head>
        <body>
        <h1>Configure Your Device</h1>
        <form action="/configure" method="post">
            Wi-Fi SSID:<br>
            <input type="text" name="ssid"><br>
            Wi-Fi Password:<br>
            <input type="password" name="password"><br>
            Timezone (UTC offset):<br>
            <input type="number" name="timezone" min="-12" max="14" value="0"><br>
            Christmas Date (MM-DD):<br>
            <input type="text" name="christmas_date" value="12-24"><br><br>
            <input type="submit" value="Save">
        </form>
        </body>
        </html>
        """
        # Send the response
        return Response(request, content_type="text/html", body=html)

    @server.route("/configure", methods=["POST"])
    def configure(request: Request):
    raw_data = request.body.decode('utf-8')
    form_data = parse_form_data(raw_data)
    ssid = form_data.get("ssid", "")
    password = form_data.get("password", "")
    timezone = int(form_data.get("timezone", "0"))
    christmas_date = form_data.get("christmas_date", "12-24")

    # Save the configuration
    config = {
        "ssid": ssid,
        "password": password,
        "timezone": timezone,
        "christmas_date": christmas_date
    }
    with open("/config.json", "w") as f:
        json.dump(config, f)

    # Display confirmation on OLED
    display_message(["Configuration saved!", "Rebooting now..."])

    # Short delay before resetting
    time.sleep(2)
    microcontroller.reset()

    html = """
    <html>
    <head><title>Configuration Saved</title></head>
    <body>
    <h1>Configuration Saved!</h1>
    <p>The device will restart shortly.</p>
    </body>
    </html>
    """
    # Send the response to the client before reset
    return Response(request, content_type="text/html", body=html)



# Custom URL decoding function
def unquote_plus(s):
    # Replace plus signs with spaces
    s = s.replace('+', ' ')
    # Decode percent-encoded characters
    res = ''
    i = 0
    while i < len(s):
        c = s[i]
        if c == '%' and i + 2 < len(s):
            hex_value = s[i+1:i+3]
            try:
                res += chr(int(hex_value, 16))
                i += 3
                continue
            except ValueError:
                pass  # Invalid hex digits
        else:
            res += c
            i += 1
    return res

# Helper function to parse form data
def parse_form_data(form_str):
    form_data = {}
    pairs = form_str.split('&')
    for pair in pairs:
        if '=' in pair:
            key, value = pair.split('=', 1)
            key = unquote_plus(key)
            value = unquote_plus(value)
            form_data[key] = value
    return form_data

# Function to load configuration
def load_configuration():
    try:
        with open("/config.json", "r") as f:
            config = json.load(f)
        return config
    except OSError as e:
        print("Configuration not found. Starting with default configuration.")
        return None  # Return None or a default config dictionary if you prefer


# Function to connect to Wi-Fi
def connect_to_wifi(ssid, password):
    wifi.radio.stop_ap()  # Stop AP mode if running
    wifi.radio.connect(ssid, password)
    max_wait = 10
    while not wifi.radio.ipv4_address and max_wait > 0:
        time.sleep(1)
        max_wait -= 1
    return wifi.radio.ipv4_address

# Function to check if BOOTSEL button is pressed
# Function to check if button on GP15 is pressed
def is_bootsel_pressed():
    button = digitalio.DigitalInOut(board.GP15)  # Change pin to GP15
    button.switch_to_input(pull=digitalio.Pull.UP)
    return not button.value  # Button pressed when value is False

# Function to synchronize time via NTP
def synchronize_time(timezone_offset):
    try:
        pool = socketpool.SocketPool(wifi.radio)
        ntp = adafruit_ntp.NTP(pool, tz_offset=timezone_offset)
        rtc.RTC().datetime = ntp.datetime
        print("Time synchronized")
    except Exception as e:
        print("Failed to synchronize time:", e)
        display_message(["Time Sync Error"])
        time.sleep(5)
        microcontroller.reset()

# Main function
def main():
    print("Starting main function...")  # Debug print
    # Check if BOOTSEL button is pressed or configuration is missing
    config = load_configuration()
    if config is None:
        print("No configuration found. Starting Access Point mode.")  # Debug print
        ip = start_access_point()
        run_configuration_server(ip)
    else:
        print("Configuration found. Connecting to Wi-Fi...")  # Debug print
        try:
            ip = connect_to_wifi(config["ssid"], config["password"])
            if not ip:
                raise Exception("Failed to connect")
            print("Connected to Wi-Fi:", ip)
            display_message(["Connected to Wi-Fi"])
        except Exception as e:
            print("Wi-Fi connection error:", e)
            display_message(["Wi-Fi Error"])
            time.sleep(5)
            microcontroller.reset()

        synchronize_time(config["timezone"])

        # Start countdown
        start_countdown(config)


def start_countdown(config):
    timezone_offset = config["timezone"]
    christmas_month, christmas_day = map(int, config["christmas_date"].split('-'))

    last_days_remaining = None

    while True:
        current_datetime = datetime.now()
        # Normalize to midnight
        current_date = datetime(current_datetime.year, current_datetime.month, current_datetime.day)
        # Determine the next Christmas date
        if current_date.month > christmas_month or (current_date.month == christmas_month and current_date.day > christmas_day):
            christmas_year = current_date.year + 1
        else:
            christmas_year = current_date.year
        christmas_date = datetime(christmas_year, christmas_month, christmas_day)
        delta = christmas_date - current_date
        days_remaining = delta.days

        if days_remaining != last_days_remaining:
            display_countdown(days_remaining)
            last_days_remaining = days_remaining
            print("Days until Christmas:", days_remaining)

        # Sleep until the next midnight
        now = datetime.now()
        next_midnight = datetime(now.year, now.month, now.day) + timedelta(days=1)
        sleep_seconds = (next_midnight - now).total_seconds()
        time.sleep(sleep_seconds + 1)

if __name__ == "__main__":
    main()
