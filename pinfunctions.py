#!/usr/bin/env python3

import usb.core
import usb.util
import time
VID = 0x1A86
PID = 0x5512
dev = usb.core.find(idVendor=VID, idProduct=PID)
if dev is None:
    raise ValueError("CH341 device not found")
if dev.is_kernel_driver_active(0):
    dev.detach_kernel_driver(0)
dev.set_configuration()
usb.util.claim_interface(dev, 0)

CMD_UIO_STREAM = 0xAB
PIN_CS   = 0x01
PIN_CLK  = 0x08
PIN_MOSI = 0x20
PIN_MISO = 0x80

# Global variable to track current GPIO state
current_gpio_state = 0x00

def write_gpio(byte0_data, byte1_data=None, byte2_data=None, byte3_data=None):
    """
    Write to all GPIO bytes with direction control
    
    Byte 0 (bits 0-7): D0-D7 pins
    Byte 1 (bits 8-15): ERR, PEMP, INT, SLCT, unknown, WAIT, READ, ADDR
    Byte 2 (bits 16-23): WRITE, SCL
    Byte 3 (bits 24-31): SDA
    """
    global current_gpio_state
    
    if byte1_data is None:  # Single byte mode (old function)
        # Special command for pins D0-D5 only
        mask = byte0_data & 0x3F
        cmd = [
            0xAB,           # UIO_STREAM command
            0x40 | 0x3F,    # UIO_DIR | 0x3F
            0x80 | mask,    # UIO_OUT | mask
            0x20            # UIO_STREAM_END
        ]
        try:
            written = dev.write(0x02, cmd, timeout=1000)
            current_gpio_state = (current_gpio_state & 0xC0) | mask
            #print(f"GPIO Write: 0x{mask:02X}")  # Debug
        except usb.core.USBError as e:
            print("USB WRITE ERROR:", e)
    else:
        # Full 4-byte mode
        cmd = [
            0xA1,           # output command
            0x6A,           # magic value
            0b11111111,     # enable mask (enable all 4 bytes)
            byte1_data,     # Byte 1 Data (0=LOW, 1=HIGH)
            0xFF,           # Byte 1 Direction (1=OUTPUT for all pins)
            byte0_data,     # Byte 0 Data
            0xFF,           # Byte 0 Direction (1=OUTPUT for all pins)
            byte2_data,     # Byte 2 Data
            0x00,           # Byte 2 Direction (must be 0x00)
            byte3_data,     # Byte 3 Data
            0x00            # Byte 3 Direction (must be 0x00)
        ]
        try:
            written = dev.write(0x02, cmd, timeout=1000)
            current_gpio_state = byte0_data
        except usb.core.USBError as e:
            print("USB WRITE ERROR:", e)

def setclk():
    """Set CLK pin HIGH without affecting other pins"""
    global current_gpio_state
    new_state = current_gpio_state | PIN_CLK
    write_gpio(new_state)

def resetclk():
    """Set CLK pin LOW without affecting other pins"""
    global current_gpio_state
    new_state = current_gpio_state & ~PIN_CLK
    write_gpio(new_state)

def setcs():
    """Set CS pin HIGH (disable chip)"""
    global current_gpio_state
    new_state = current_gpio_state | PIN_CS
    write_gpio(new_state)

def resetcs():
    """Set CS pin LOW (enable chip)"""
    global current_gpio_state
    new_state = current_gpio_state & ~PIN_CS
    write_gpio(new_state)

def setmosi():
    """Set MOSI pin HIGH without affecting other pins"""
    global current_gpio_state
    new_state = current_gpio_state | PIN_MOSI
    write_gpio(new_state)

def resetmosi():
    """Set MOSI pin LOW without affecting other pins"""
    global current_gpio_state
    new_state = current_gpio_state & ~PIN_MOSI
    write_gpio(new_state)

def read_gpio():
    cmd = [0xA0]  # INPUT command
    dev.write(0x02, cmd)
    data = dev.read(0x82, 6)  # Read 6 bytes
    return data

def read_tlc1549():
    """Read from TLC1549 ADC"""
    result = 0
    
    # Start conversion: Pull CS low
    resetcs()  # CS LOW to enable chip
    time.sleep(0.00001)  # 10us delay for chip enable
    
    # Read 16 bits (TLC1549 outputs data on falling edge of CLK)
    for i in range(16):
        # Read bit before clock edge (for falling edge output)
        status = read_gpio()
        bit = 1 if (status[0] & PIN_MISO) else 0
        result = (result << 1) | bit
        
        # Toggle clock
        setclk()   # CLK HIGH
        time.sleep(0.000001)  # 1us delay
        resetclk() # CLK LOW
        time.sleep(0.000001)  # 1us delay
    
    # End conversion: Pull CS high
    setcs()  # CS HIGH to disable chip
    
    # The TLC1549 outputs 16 bits, but only the first 10 are valid
    # The first 6 bits are leading zeros or configuration bits
    result = result & 0x3FF  # Keep only lower 10 bits
    
    return result

def debug_pins():
    """Debug function to check pin states"""
    print("\n--- Debug Info ---")
    print(f"Current GPIO state: 0x{current_gpio_state:02X}")
    status = read_gpio()
    print(f"Read GPIO: {[hex(x) for x in status]}")
    print(f"PIN_CS (0x01): {'HIGH' if status[0] & PIN_CS else 'LOW'}")
    print(f"PIN_CLK (0x08): {'HIGH' if status[0] & PIN_CLK else 'LOW'}")
    print(f"PIN_MOSI (0x20): {'HIGH' if status[0] & PIN_MOSI else 'LOW'}")
    print(f"PIN_MISO (0x80): {'HIGH' if status[0] & PIN_MISO else 'LOW'}")
    print("-----------------\n")

# Initialize
init_buf = [
    0xAB,   # CMD_UIO_STREAM
    0x40,   # enable output
    0x20    # end
]
dev.write(0x02, init_buf, timeout=1000)
print("GPIO mode initialized")

# Initialize all pins to LOW
write_gpio(0x00)
time.sleep(0.1)

# Debug initial state
debug_pins()

# Test pin toggling
print("Testing CS pin toggling...")
resetcs()  # CS LOW
time.sleep(0.1)
debug_pins()
setcs()    # CS HIGH
time.sleep(0.1)
debug_pins()

print("Starting ADC readings...\n")

while True:
    adc = read_tlc1549()
    voltage = adc * 5.0 / 1023.0
    print(f"ADC={adc:4d} (0x{adc:03X}) Voltage={voltage:.3f}V")    
    time.sleep(0.5)
