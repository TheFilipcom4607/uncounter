import storage
import supervisor

# Disable USB drive access to make the filesystem writable
storage.disable_usb_drive()

# Disable auto-reload feature
supervisor.runtime.autoreload = False
