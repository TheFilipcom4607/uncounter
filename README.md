# (Un)Counter

<div align="center">
  <img src="https://socialify.git.ci/thefilipcom4607/uncounter/image?font=Source%20Code%20Pro&language=1&name=1&owner=1&pattern=Circuit%20Board&theme=Dark" alt="UnCounter Project Banner">

  A minimalist desk companion that counts down to your important dates, powered by ESP32.
</div>

## Overview

UnCounter is a compact, battery-powered device that helps you keep track of time until significant dates. With its sleek OLED display and automatic time synchronization, it's the perfect desk accessory for counting down to deadlines, events, or any meaningful date.

<div align="center">
  <img src="https://assets.thefilip.com/uncounter.jpg" alt="UnCounter Device" width="400">
</div>

## ✨ Features

- **Hardware**
  - ESP32-S3 (I used C3)
  - 0.96" OLED display
  - Lipo battery
  - USB-C charging with TP4056 charger
  
- **Software**
  - Automatic time synchronization via NTP
  - Web-based configuration through AP mode
  - Over-the-air (OTA) updates support (coming soon)

## 🛠️ Hardware Requirements

- ESP32-C3 Super Mini
- 0.96" OLED Display (SSD1306 or compatible)
- TP4056 USB-C charging module
- LiPo battery
- Wires
- 3D printed case (i suck at designing 3d models; this is not model which i dont have permision to share)

## 📥 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/TheFilipcom4607/uncounter
   ```

2. Navigate to the project directory:

3. Before flashing:
   - Ensure your ESP32-S3 is flashed with circuitpython and its connected
   - Make sure you have adequate USB-C cable for data transfer

4. Flash the device:
   - Connect your flashed ESP32-S3
   - Copy all contents from the directory (excluding README.md) to the device
   - Restart the device to apply changes

## 🔧 Initial Setup

1. On first boot, the device will create a WiFi access point named "Counter-Setup"
2. Connect to this network using your smartphone or computer
3. Navigate to the configuration portal (192.168.4.1) with the password displayed on screen
4. Set your target date and configure WiFi credentials
5. The device will automatically reboot, sync time and begin countdown

## 📱 Usage

- The OLED display shows the countdown
- Time automatically syncs daily to maintain accuracy
- Short the reset pin (15) to ground to enter configuration mode

## ⚡ Power Management

(with 750mah battery)

- Battery life: ~2 days with normal usage
- Charging time: approximately 2 hours


## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

If you encounter any issues or have questions:
Open an issue on GitHub

---

Made with ❤️ by [TheFilipcom4607](https://github.com/TheFilipcom4607)
