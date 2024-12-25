import asyncio
import socket
import _thread
import machine  # type: ignore
from machine import Pin, SoftI2C  # type: ignore

import wifimgr
import AJXServer
import ssd1306
from configmgr import ConfigFile

# Initialize pins
led = Pin(2, Pin.OUT)
relay_out_pin = Pin(33, Pin.OUT)
tank_switch_pin = Pin(36, Pin.IN, Pin.PULL_UP)

# Initialize global variables
server = None
ip_address = "wait for wifi"
relay_state = False
set_on_time = 0
set_off_time = 0
timer_seconds = 0
elapsed_time_s = 0
elapsed_time_m = 0
tank_water_state = False

# Initialize I2C and display
i2c = SoftI2C(sda=Pin(14), scl=Pin(13))
display = ssd1306.SSD1306_I2C(128, 32, i2c)


async def timer_counter():
    global timer_seconds, ip_address, relay_state, elapsed_time_s, elapsed_time_m

    myconfigfile = ConfigFile('configuration.conf')
    myconfigfile.read()
    myconfig = myconfigfile.config
    on_time_str = str(myconfig['timer']['ontime'])
    off_time_str = str(myconfig['timer']['offtime'])

    while True:
        elapsed_time_s = int(timer_seconds % 60)
        elapsed_time_m = int(timer_seconds / 60)
        print(
            f"timer counter: {timer_seconds} elapsed time >> {elapsed_time_m} : {elapsed_time_s}")

        display.fill(0)
        display.text(str(ip_address), 0, 0, 1)
        if relay_state:
            display.text(on_time_str + " <", 0, 13, 1)
            display.text(off_time_str, 64, 13, 1)
        else:
            display.text(on_time_str, 0, 13, 1)
            display.text("> " + off_time_str, 64, 13, 1)
        display.text(str(elapsed_time_m), 10, 24, 1)
        display.text(":", 50, 24, 1)
        display.text(str(elapsed_time_s), 60, 24, 1)
        if tank_water_state:
            display.fill_rect(117, 24, 127, 31, 1)
        display.show()

        await asyncio.sleep(1)
        timer_seconds += 1


async def relay_switcher():
    global timer_seconds, elapsed_time_m, relay_state

    myconfigfile = ConfigFile('configuration.conf')
    myconfigfile.read()
    myconfig = myconfigfile.config

    while True:
        if relay_state:
            if elapsed_time_m >= myconfig['timer']['ontime']:
                relay_state = False
                timer_seconds = 0
                relay_out_pin.off()
                print("relay turned off")
        else:
            if (elapsed_time_m >= myconfig['timer']['offtime']) and not tank_water_state:
                relay_state = True
                timer_seconds = 0
                relay_out_pin.on()
                print("relay turned on")
        await asyncio.sleep(1)


async def tank_water_level():
    global tank_water_state

    while True:
        if tank_switch_pin.value() == 0:
            tank_water_state = True
            print("tank water level is full")
        else:
            tank_water_state = False
            print("tank water level is low")
        await asyncio.sleep(1)


async def main():
    timer_task = asyncio.create_task(timer_counter())
    relay_switcher_task = asyncio.create_task(relay_switcher())
    tank_water_level_task = asyncio.create_task(tank_water_level())
    await asyncio.gather(timer_task, relay_switcher_task, tank_water_level_task)


def configure_main(delay, id):
    global server, ip_address

    myconfigfile = ConfigFile('configuration.conf')
    myconfigfile.read()
    myconfig = myconfigfile.config
    print("configurations loaded")

    wlan = wifimgr.get_connection()
    if wlan is None:
        print("Could not initialize the network connection.")
        while True:
            pass

    ip_address = wlan.ifconfig()[0]
    print("ESP OK")

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('', 80))
        s.listen(5)
    except OSError:
        machine.reset()

    server = AJXServer.AJXServer(s)
    server.on_time_value = myconfig['timer']['ontime']
    server.off_time_value = myconfig['timer']['offtime']
    print(server.on_time_value)
    print(server.off_time_value)

    config_changed = False
    while True:
        try:
            server.start()
        except OSError:
            print("server crashed, resetting!")
            machine.reset()

        server._elapsed_time = timer_seconds
        server._tank_state = tank_water_state
        if myconfig['timer']['ontime'] != server.on_time_value:
            config_changed = True
            myconfig['timer']['ontime'] = server.on_time_value
            print("config change", server.on_time_value)
            myconfigfile.write(myconfig)
        if myconfig['timer']['offtime'] != server.off_time_value:
            config_changed = True
            myconfig['timer']['offtime'] = server.off_time_value
            print("config change", server.off_time_value)
            myconfigfile.write(myconfig)

        if config_changed:
            machine.reset()


print("wifi task created")
_thread.start_new_thread(configure_main, (1, 1))
print("wifi task ok")

print("main task created")
asyncio.run(main())
