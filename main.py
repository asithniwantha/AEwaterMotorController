import wifimgr
import machine  # type: ignore
from machine import Pin, SoftI2C  # type: ignore
import asyncio
import _thread
import socket
import AJXServer
import ssd1306
from configmgr import *


led = machine.Pin(2, machine.Pin.OUT)
relay_out_pin = machine.Pin(33, machine.Pin.OUT)
tank_switch_pin = machine.Pin(36, machine.Pin.IN, Pin.PULL_UP)

global server
global ip_address
global relayState

relayState = False
set_on_time = 0
set_off_time = 0
timer_seconds = 0
elapsed_time_s = 0
elapsed_time_m = 0

# using default address 0x3C
i2c = SoftI2C(sda=Pin(13), scl=Pin(14))
display = ssd1306.SSD1306_I2C(128, 32, i2c)


async def timer_counter():
    global timer_seconds
    global ip_address
    global myconfig
    global relayState
    global elapsed_time_s
    global elapsed_time_m
    ip_address = "wait for wifi"

    myconfigfile = ConfigFile('configuration.conf')
    myconfigfile.read()
    myconfig = myconfigfile.config
    onTimeStr = str(myconfig['timer']['ontime'])
    offTimeStr = str(myconfig['timer']['offtime'])

    while True:
        elapsed_time_s = int(timer_seconds % 60)
        elapsed_time_m = int(timer_seconds/60)
        print("timer counter : ", timer_seconds,
              "       elapsed time  >>", elapsed_time_m, " : ", elapsed_time_s)
        display.fill(0)
        display.text(str(ip_address), 0, 0, 1)
        if relayState:
            display.text(onTimeStr + " <", 0, 13, 1)
            display.text(offTimeStr, 64, 13, 1)
        else:
            display.text(onTimeStr, 0, 13, 1)
            display.text("> " + offTimeStr, 64, 13, 1)
        display.text(str(int(timer_seconds/60)), 10, 24, 1)
        display.text(":", 50, 24, 1)
        display.text(str(int(timer_seconds % 60)), 60, 24, 1)
        display.show()
        await asyncio.sleep_ms(1000)  # type: ignore
        timer_seconds += 1


async def relaySwitcher():
    global timer_seconds
    global elapsed_time_m
    global myconfig
    global relayState
    relayState = False

    while True:
        if relayState:
            if elapsed_time_m >= myconfig['timer']['ontime']:
                relayState = False
                timer_seconds = 0
                relay_out_pin.off()
                print("relay turned off")
        else:
            if elapsed_time_m >= myconfig['timer']['offtime']:
                relayState = True
                timer_seconds = 0
                relay_out_pin.on()
                print("relay turned on")
        await asyncio.sleep(1)


async def main():
    timerTask = asyncio.create_task(timer_counter())
    relaySwitcherTask = asyncio.create_task(relaySwitcher())
    while True:
        await asyncio.sleep(.001)
    machine.reset()


def configure_main(delay, id):
    global server
    global ip_address
    global myconfig

    myconfigfile = ConfigFile('configuration.conf')
    myconfigfile.read()
    myconfig = myconfigfile.config
    print("configurations loaded")

    print("starting server")
    wlan = wifimgr.get_connection()
    if wlan is None:
        print("Could not initialize the network connection.")
        while True:
            pass
    # Main Code goes here, wlan is a working network.WLAN(STA_IF) instance.
    print("ESP OK")
    ip_address = wlan.ifconfig()[0]

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('', 80))
        s.listen(5)
    except OSError as e:
        machine.reset()

    server = AJXServer.AJXServer(s)
    server.on_time_value = myconfig['timer']['ontime']
    server.off_time_value = myconfig['timer']['offtime']
    print(server.on_time_value)
    print(server.off_time_value)

    configChanged = False
    while True:
        try:
            server.start()
        except OSError as e:
            machine.reset()
        server._elapsed_time = timer_seconds
        if myconfig['timer']['ontime'] != server.on_time_value:
            configChanged = True
            myconfig['timer']['ontime'] = server.on_time_value
            print("config change", server.on_time_value)
            myconfigfile.write(myconfig)
        if myconfig['timer']['offtime'] != server.off_time_value:
            configChanged = True
            myconfig['timer']['offtime'] = server.off_time_value
            print("config change", server.off_time_value)
            myconfigfile.write(myconfig)

        if configChanged:
            machine.reset()
    machine.reset()


print("wifi task created")
_thread.start_new_thread(configure_main, (1, 1))
print("wifi task ok")

print("main task created")
asyncio.run(main())
