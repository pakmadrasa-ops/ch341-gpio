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


def write_gpio(byte0_data, byte1_data, byte2_data, byte3_data):
    """
    Write to all GPIO bytes with direction control
    
    Byte 0 (bits 0-7): D0-D7 pins
    Byte 1 (bits 8-15): ERR, PEMP, INT, SLCT, unknown, WAIT, READ, ADDR
    Byte 2 (bits 16-23): WRITE, SCL
    Byte 3 (bits 24-31): SDA
    """
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
    except usb.core.USBError as e:
        print("USB WRITE ERROR:", e)    
        
def write_gpio(mask):
    """
    Special command for pins D0-D5 only
    mask bits: 0x01=D0, 0x02=D1, 0x04=D2, 0x08=D3, 0x10=D4, 0x20=D5
    """
    cmd = [
        0xAB,           # UIO_STREAM command
        0x40 | 0x3F,    # UIO_DIR | 0x3F
        0x80 | (mask & 0x3F),  # UIO_OUT | mask
        0x20            # UIO_STREAM_END
    ]
    try:
        written = dev.write(0x02, cmd, timeout=1000)
        #print(f"WRITE OK: {written} bytes")
    except usb.core.USBError as e:
        print("USB WRITE ERROR:", e)    
    

def read_gpio():
    cmd = [0xA0]  # INPUT command
    dev.write(0x02, cmd)
    data = dev.read(0x82, 6)  # Read 6 bytes
    # Byte 0 data = data[0]
    # Byte 1 data = data[1]
    return data

def read_tlc1549():
    result = 0
    write_gpio(0x00)
    for i in range(16):
        write_gpio(0x00)
        status = read_gpio()
        bit = 1 if (status[0] & PIN_MISO) else 0
        result = (result << 1) | bit
        write_gpio(PIN_CLK)
    write_gpio(PIN_CS)
    result = (result >> 6) & 0x3FF
    return result


init_buf = [
    0xAB,   # CMD_UIO_STREAM
    0x40,   # enable output
    0x20    # end
]
dev.write(0x02, init_buf, timeout=1000)
print("GPIO mode initialized")



#write_gpio(0xff)
write_gpio(0xff)

status = read_gpio()
print(status) 

while True:
    adc = read_tlc1549()
    voltage = adc * 5.0 / 1023.0
    print(f"ADC={adc} Voltage={voltage:.3f}V")
    time.sleep(0.5)
