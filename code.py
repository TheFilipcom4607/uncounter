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
        display_message(["Configuration saved!", "Resetting..."])

        html = """
        <html>
        <head><title>Configuration Saved</title></head>
        <body>
        <h1>Configuration Saved!</h1>
        <p>The device will restart shortly.</p>
        </body>
        </html>
        """
        # Send HTTP response
        response = Response(request, content_type="text/html", body=html)
        response.send()

        # Stop the server and access point after a short delay
        time.sleep(2)  # Allow response to reach client
        print("Stopping server and access point...")
        server.stop()
        wifi.radio.stop_ap()

        # Reset the microcontroller
        time.sleep(3)  # Delay for user to see OLED message
        microcontroller.reset()

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

# Main function
def main():
    print("Starting main function...")

    config = load_configuration()
    if config is None:
        print("No configuration found. Starting Access Point mode.")
        ip = start_access_point()
        run_configuration_server(ip)
    else:
        print("Configuration found. Connecting to Wi-Fi...")
        # Existing functionality to use the loaded configuration
        pass

if __name__ == "__main__":
    main()
