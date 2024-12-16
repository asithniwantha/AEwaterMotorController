import wifimgr
import machine
from machine import Pin, SoftI2C
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

set_on_time = 0
set_off_time = 0
timer_seconds = 0

# using default address 0x3C
i2c = SoftI2C(sda=Pin(13), scl=Pin(14))
display = ssd1306.SSD1306_I2C(128, 32, i2c)


async def timer_counter():
    global timer_seconds
    global ip_address
    global server
    server = None
    ip_address = "wait for wifi"

    while True:
        print("timer counter : ", timer_seconds)
        display.fill(0)
        display.text(str(ip_address), 0, 0, 1)
        if server is not None:
            display.text(str(server.on_time_value), 0, 13, 1)
            display.text(str(server.off_time_value), 64, 13, 1)
        display.text(str(int(timer_seconds/60)), 0, 24, 1)
        display.text(" : ", 10, 24, 1)
        display.text(str(int(timer_seconds % 60)), 20, 24, 1)
        display.show()
        await asyncio.sleep_ms(1000)  # type: ignore
        timer_seconds += 1 


async def p():
    while True:
        a = 0
        print("p")
        await asyncio.sleep(4)


async def main():
    pfn = asyncio.create_task(p())
    ppfn = asyncio.create_task(timer_counter())
    while True:
        await asyncio.sleep(.001)
    machine.reset()


def configure_main(delay, id):
    global server
    global ip_address
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

    myconfigfile = ConfigFile('configuration.conf')
    myconfigfile.read()
    myconfig = myconfigfile.config
    pfn = asyncio.create_task(p())

    server = AJXServer.AJXServer(s)
    server.on_time_value = myconfig['timer']['ontime']
    server.off_time_value = myconfig['timer']['offtime']
    print(server.on_time_value)
    print(server.off_time_value)

    while True:
        server.start()
        server._elapsed_time = timer_seconds
        if myconfig['timer']['ontime'] != server.on_time_value:
            myconfig['timer']['ontime'] = server.on_time_value
            print("config change", server.on_time_value)
            myconfigfile.write(myconfig)
        if myconfig['timer']['offtime'] != server.off_time_value:
            myconfig['timer']['offtime'] = server.off_time_value
            print("config change", server.off_time_value)
            myconfigfile.write(myconfig)
    machine.reset()


print("wifi task created")
_thread.start_new_thread(configure_main, (1, 1))
print("wifi task ok")

print("main task created")
asyncio.run(main())
