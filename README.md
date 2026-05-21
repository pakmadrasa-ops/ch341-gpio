# ch341-gpio
Using CH341 as a USB GPIO and custom serial interface playground

QinHeng Electronics devices are everywhere — USB programmers, EEPROM tools, UART adapters, SPI dongles, printer cables, and random low-cost gadgets.

Most people only use the UART mode.

But the CH341 can do much more.

This project shows how to:

* Use the CH341 as a **general purpose GPIO device**
* Implement **custom serial protocols** in software
* Bitbang interfaces like:

  * SPI
  * Shift registers
  * ADCs
  * Custom synchronous protocols
* Read sensors and external hardware directly from Python
* Experiment with reverse engineering and embedded systems

This repository demonstrates reading a:

* TLC1549 ADC
* using pure GPIO bitbanging from Python over USB.

---

# Why This Is Interesting

The CH341 mini programmer is extremely cheap and widely available.

That means you can build:

* USB GPIO adapters
* Logic analyzers
* Simple programmers
* Custom SPI/I2C tools
* Retro hardware interfaces
* Experimental buses
* Industrial control hacks
* Embedded debugging tools

…without designing custom USB firmware.

The USB protocol handling is already inside the CH341.

Python simply sends command packets.

---

# Features

✅ Direct USB access using PyUSB
✅ No kernel driver required while running
✅ Bitbang GPIO control
✅ Software SPI-like interface
✅ Read external ADCs
✅ Easy to modify for other protocols
✅ Works on Linux
✅ Great for tinkerers and reverse engineers

---

# Hardware Used

## Main Device

* CH341 / CH341A / CH341B USB chip

## Example ADC

* TLC1549

The TLC1549 is a 10-bit serial ADC with a very simple clocked interface, making it perfect for GPIO bitbanging experiments.

---

# Repository Goal

The goal of this repository is not just this ADC example.

It is to document how the CH341 GPIO engine works so people can build:

* custom interfaces
* weird protocols
* laboratory tools
* EEPROM programmers
* FPGA loaders
* GPIO automation
* sensor readers
* industrial hacks

using inexpensive hardware.

---

# Installation

## Install Dependencies

### Debian / Ubuntu

```bash
sudo apt install python3-usb
```

### Or with pip

```bash
pip install pyusb
```

---

# Running

```bash
python3 tlc1549.py
```

Example output:

```text
GPIO mode initialized
ADC=512 Voltage=2.502V
ADC=514 Voltage=2.512V
ADC=511 Voltage=2.497V
```

---

# Understanding The Code

---

# 1. Finding The Device

```python
VID = 0x1A86
PID = 0x5512

dev = usb.core.find(idVendor=VID, idProduct=PID)
```

This locates the CH341 USB device.

Vendor ID `0x1A86` belongs to WCH/QinHeng.

---

# 2. Detaching Linux Kernel Driver

```python
if dev.is_kernel_driver_active(0):
    dev.detach_kernel_driver(0)
```

Linux may automatically attach a driver.

We detach it so Python can directly control the USB interface.

---

# 3. GPIO Mode Initialization

```python
init_buf = [
    0xAB,
    0x40,
    0x20
]
```

This enables the CH341 UIO stream mode.

The magic values are part of undocumented / semi-documented CH341 commands discovered through experimentation and reverse engineering.

---

# 4. GPIO Writing

```python
write_gpio(mask)
```

This function controls GPIO pins D0–D5.

Example:

```python
write_gpio(0x08)
```

sets D3 HIGH.

---

# Pin Mapping

| Bit  | Pin |
| ---- | --- |
| 0x01 | D0  |
| 0x02 | D1  |
| 0x04 | D2  |
| 0x08 | D3  |
| 0x10 | D4  |
| 0x20 | D5  |

---

# 5. Reading GPIO

```python
status = read_gpio()
```

Reads CH341 GPIO input states.

The returned buffer contains multiple status bytes from the chip.

---

# 6. Software SPI / Bitbanging

The ADC communication is implemented manually.

No hardware SPI peripheral is used.

This is the important part:

```python
write_gpio(0x00)
status = read_gpio()
bit = 1 if (status[0] & PIN_MISO) else 0
write_gpio(PIN_CLK)
```

The code:

1. Pulls clock LOW
2. Reads MISO
3. Pulls clock HIGH
4. Repeats 16 times

This is essentially a software-generated SPI clock.

---

# TLC1549 Read Sequence

The ADC returns serial bits one-by-one.

The loop reconstructs the final 10-bit ADC value.

```python
result = (result << 1) | bit
```

This shifts incoming bits into the result variable.

Finally:

```python
result = (result >> 6) & 0x3FF
```

extracts the actual 10-bit ADC value.

---

# Voltage Conversion

```python
voltage = adc * 5.0 / 1023.0
```

Converts the ADC value into voltage assuming:

* 5V reference
* 10-bit resolution

---

# CH341 GPIO Timing Notes

This is USB bitbanging.

So it is:

* much slower than microcontroller GPIO
* not real-time
* affected by USB latency

But it is still useful for:

* slow SPI devices
* ADCs
* EEPROMs
* GPIO automation
* debugging
* retro hardware
* experiments

---

# Ideas For Future Projects

You can extend this project into:

## Interfaces

* SPI Flash programmer
* I2C master
* SWD/JTAG experiments
* Shift register controller
* LED matrix driver

## Hardware Hacking

* BIOS flashing
* Logic probing
* Reverse engineering
* Bus sniffing
* Sensor interfacing

## Automation

* Relay controller
* Industrial GPIO
* Lab instrumentation
* Test fixtures

---

# Example Wiring

## CH341 → TLC1549

| CH341      | TLC1549         |
| ---------- | --------------- |
| D0         | CS              |
| D3         | CLK             |
| D5         | MOSI (optional) |
| MISO input | DATA OUT        |
| GND        | GND             |
| 5V         | VCC             |

---

## CH341 Mini Programmer Jumpers Explained

Many cheap CH341A Mini Programmer boards include jumpers or solder links that change how the CH341 chip operates.

This is important because the same chip can appear as completely different USB devices depending on jumper configuration.

Example from Linux:

### EEPROM / Parallel / I2C Mode

```text
ID 1a86:5512 QinHeng Electronics CH341 in EPP/MEM/I2C mode
```

This mode exposes the special GPIO / memory / parallel interface features used in this repository.

This is the mode required for:

* GPIO control
* Bitbanging
* EEPROM programming
* Custom serial interfaces
* SPI/I2C experiments

---

### UART Serial Mode

```text
ID 1a86:5523 QinHeng Electronics CH341 in serial mode
```

This turns the chip into a normal USB-to-UART adapter.

In this mode:

* GPIO features are unavailable
* UIO stream commands do not work
* The device behaves like `/dev/ttyUSB0`

---

# Why This Happens

The CH341 supports multiple internal operating modes:

| Mode | Function                      |
| ---- | ----------------------------- |
| UART | USB-to-serial converter       |
| EPP  | Parallel/GPIO style interface |
| MEM  | EEPROM/flash programming      |
| I2C  | Serial memory interface       |

Cheap CH341 programmer boards expose configuration jumpers that select which mode is active.

---

# Typical CH341A Programmer Jumpers

Different board revisions vary, but common jumpers include:

| Jumper        | Purpose                          |
| ------------- | -------------------------------- |
| 3.3V / 5V     | Target voltage selection         |
| UART / PROG   | Select serial vs programmer mode |

Some boards use:

* slide switches
* solder bridges
* resistor options
* zero-ohm links

instead of removable jumpers.

---

# Detecting The Active Mode

Linux makes this easy:

```bash
lsusb
```

If you see:

```text
1a86:5512
```

the device is in programmable GPIO/EPP/I2C mode.

If you see:

```text
1a86:5523
```

the device is acting as a UART adapter.

---

# Important For This Repository

This project requires:

```text
VID:PID = 1A86:5512
```

because the GPIO and UIO stream commands only work in EPP/MEM/I2C mode.

If your board appears as:

```text
1A86:5523
```

you likely need to:

* move a jumper
* change a switch
* modify solder bridges

to enable programmer/EPP mode.

---




# Important Notes

⚠ GPIO functionality differs between CH341 variants.

⚠ Some pins are input-only.

⚠ Some command formats are poorly documented.

⚠ Timing-sensitive protocols may not work reliably.

⚠ Use level shifting when interfacing 3.3V hardware.

---

# Learning Value

This project is useful for learning:

* USB device communication
* Bitbanging
* SPI fundamentals
* Reverse engineering
* Embedded Linux
* PyUSB
* Low-level hardware hacking

---

# Credits

* PyUSB developers
* Reverse engineering community
* WCH / QinHeng
* Hardware hackers documenting undocumented chips

---

# License

MIT License

Hack responsibly
