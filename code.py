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
    y = 4
    for line in lines:
        text_area = label.Label(terminalio.FONT, text=line, color=0xFFFFFF, x=0, y=y)
        splash.append(text_area)
        y += 11
    display.root_group = splash  # Correct way to set the root group on OLED

# Function to check if safe mode should be entered (if GPIO14 is grounded)
def check_for_safe_mode():
    pin = digitalio.DigitalInOut(board.GP14)
    pin.switch_to_input(pull=digitalio.Pull.UP)
    return not pin.value

# Function to check if reconfiguration mode should be entered (if GPIO15 is grounded)
def check_for_reconfigure():
    pin = digitalio.DigitalInOut(board.GP15)
    pin.switch_to_input(pull=digitalio.Pull.UP)
    return not pin.value

if check_for_safe_mode():
    try:
        storage.remount("/", readonly=False)
        os.rename("/boot.py", "/but.py")
        display_message(["Safe mode entered.", "Rebooting now."])
        time.sleep(2)
        microcontroller.reset()
    except Exception as e:
        print("Failed to enter safe mode:", e)

# Function to display the countdown on the OLED screen
def display_countdown(days_remaining, target_label):
    splash = displayio.Group()
    title_text = f"Days until {target_label}"
    title_area = label.Label(terminalio.FONT, text=title_text, color=0xFFFFFF, scale=1)
    title_area.x = (WIDTH - title_area.bounding_box[2]) // 2
    title_area.y = 5
    splash.append(title_area)

    days_text = str(days_remaining)
    days_area = label.Label(terminalio.FONT, text=days_text, color=0xFFFFFF, scale=6)
    days_area.x = 30
    days_area.y = 40
    splash.append(days_area)
    display.root_group = splash  # Set the root group on OLED

# Function to start access point mode with stabilization delay
def start_access_point():
    ap_ssid = "Countdown-Setup"
    ap_password = f"{random.randint(0, 99999999):08}"  # 8-digit random password
    wifi.radio.stop_station()
    wifi.radio.start_ap(ssid=ap_ssid, password=ap_password)

    max_wait = 10
    while not wifi.radio.ipv4_address_ap and max_wait > 0:
        time.sleep(1)
        max_wait -= 1

    time.sleep(2)  # Stabilization time for AP mode
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

# Function to run the configuration web server
def run_configuration_server(ip):
    from adafruit_httpserver import Server, Request, Response, MIMETypes

    pool = socketpool.SocketPool(wifi.radio)
    server = Server(pool, "/static")

    @server.route("/", methods=["GET"])
    def index(request: Request):
        html = """
        <html>
        <head><title>Countdown Configuration</title></head>
        <body>
        <h1>Configure Your Countdown</h1>
        <form action="/configure" method="post">
            Wi-Fi SSID:<br>
            <input type="text" name="ssid"><br>
            Wi-Fi Password:<br>
            <input type="password" name="password"><br>
            Timezone (UTC offset):<br>
            <input type="number" name="timezone" min="-12" max="14" value="0"><br>
            Target Date (MM-DD):<br>
            <input type="text" name="target_date" value="12-24"><br>
            Countdown Label:<br>
            <input type="text" name="target_label" value="Event"><br><br>
            <input type="submit" value="Save">
        </form>
        </body>
        </html>
        """
        return Response(request, content_type="text/html", body=html)

    @server.route("/configure", methods=["POST"])
    def configure(request: Request):
        raw_data = request.body.decode('utf-8')
        form_data = parse_form_data(raw_data)
        ssid = form_data.get("ssid", "")
        password = form_data.get("password", "")
        timezone = int(form_data.get("timezone", "0"))
        target_date = form_data.get("target_date", "12-24")
        target_label = form_data.get("target_label", "Event")

        # Save the configuration
        config = {
            "ssid": ssid,
            "password": password,
            "timezone": timezone,
            "target_date": target_date,
            "target_label": target_label
        }
        with open("/config.json", "w") as f:
            json.dump(config, f)

        # Display confirmation on OLED
        display_message(["Configuration saved!", "Rebooting now..."])

        time.sleep(2)  # Delay before resetting
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
        return Response(request, content_type="text/html", body=html)

    print("Starting configuration server...")

    try:
        server.start(str(ip), port=8080)
        print(f"Configuration server running at http://{ip}:8080")
    except Exception as e:
        print("Server failed to start:", e)
        return

    while True:
        try:
            server.poll()
        except Exception as e:
            print("Server error:", e)
            time.sleep(1)
            continue

# Helper functions for URL decoding and form data parsing
def unquote_plus(s):
    s = s.replace('+', ' ')
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
                pass
        else:
            res += c
            i += 1
    return res

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

# Functions for loading configuration, connecting to Wi-Fi, and time sync
def load_configuration():
    try:
        with open("/config.json", "r") as f:
            config = json.load(f)
        # Set default values for new keys if they are missing
        if "target_date" not in config:
            config["target_date"] = "12-24"  # Default to Christmas
        if "target_label" not in config:
            config["target_label"] = "Christmas"  # Default label
        return config
    except OSError as e:
        print("Configuration not found. Starting with default configuration.")
        return None


def connect_to_wifi(ssid, password):
    wifi.radio.stop_ap()
    wifi.radio.connect(ssid, password)
    max_wait = 10
    while not wifi.radio.ipv4_address and max_wait > 0:
        time.sleep(1)
        max_wait -= 1
    return wifi.radio.ipv4_address

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

def start_countdown(config):
    timezone_offset = config["timezone"]
    target_month, target_day = map(int, config["target_date"].split('-'))
    target_label = config.get("target_label", "Event")

    last_days_remaining = None

    while True:
        current_datetime = datetime.now()
        current_date = datetime(current_datetime.year, current_datetime.month, current_datetime.day)
        if current_date.month > target_month or (current_date.month == target_month and current_date.day > target_day):
            target_year = current_date.year + 1
        else:
            target_year = current_date.year
        target_date = datetime(target_year, target_month, target_day)
        delta = target_date - current_date
        days_remaining = delta.days

        if days_remaining != last_days_remaining:
            display_countdown(days_remaining, target_label)
            last_days_remaining = days_remaining
            print(f"Days until {target_label}:", days_remaining)

        now = datetime.now()
        next_midnight = datetime(now.year, now.month, now.day) + timedelta(days=1)
        sleep_seconds = (next_midnight - now).total_seconds()
        time.sleep(sleep_seconds + 1)

# Main function
def main():
    print("Starting main function...")

    # Check if GPIO15 is grounded to enter reconfiguration mode
    if check_for_reconfigure():
        print("Reconfiguration button pressed. Deleting config and starting AP mode.")
        try:
            storage.remount("/", readonly=False)
            os.remove("/config.json")
            display_message(["Reconfiguring...", "Restarting..."])
            time.sleep(2)
            microcontroller.reset()
        except Exception as e:
            print("Failed to delete config:", e)
            display_message(["Error resetting config.", "Restarting..."])
            time.sleep(1)
            microcontroller.reset()

    config = load_configuration()
    if config is None:
        print("No configuration found. Starting Access Point mode.")
        ip = start_access_point()
        run_configuration_server(ip)
    else:
        print("Configuration found. Connecting to Wi-Fi...")
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
        start_countdown(config)

if __name__ == "__main__":
    main()
