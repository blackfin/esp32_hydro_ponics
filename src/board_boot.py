import upip
import utime, network

print('RUN: boot.py')
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
if not wlan.isconnected():
    print('connecting to network...')
    wlan.connect("t0mcruzz", "RvM@55#2891")
    while not wlan.isconnected():
        pass
print('network config:', wlan.ifconfig())
ip = wlan.ifconfig()[0]

upip.install("micropython-mcron")
upip.install('micropython-uasyncio')
upip.install('micropython-uasyncio.synchro')
upip.install('micropython-uasyncio.queues')