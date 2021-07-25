# esp32_hydro_ponics
sudo apt-get install python3-pip
pip3 install esptool
pip3 install pyserial

sudo usermod -a -G tty yourname

esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash

````
bat@nico:~/esp32/micropython-example$ esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash
esptool.py v3.1
Serial port /dev/ttyUSB0
Connecting........_____....._____....._____...
Chip is ESP32-D0WDQ6 (revision 1)
Features: WiFi, BT, Dual Core, 240MHz, VRef calibration in efuse, Coding Scheme None
Crystal is 40MHz
MAC: 3c:61:05:1b:b6:e4
Uploading stub...
Running stub...
Stub running...
Erasing flash (this may take a while)...
Chip erase completed successfully in 15.8s
Hard resetting via RTS pin...
````

From then on program the firmware starting at address 0x1000:


esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x1000 esp32-20190125-v1.10.bin

picocom -b 115200 /dev/ttyUSB0


sudo adduser myusername dialout (requires reboot)
sudo apt-get install picocom

picocom -b 115200 /dev/ttyUSB0
use CTRL-A plus CTRL-X to exit

python prompt:  use CTRL-C to break, CTRL-D for soft reboot


nstalling to: /lib/
Warning: micropython.org SSL certificate is not validated
Installing micropython-mcron 1.1.0 from https://files.pythonhosted.org/packages/0b/3f/a4001776e41541a5cab2eba457c6f81416c6381818adf8b6b71b91abc376/micropython-mcron-1.1.0.tar.gz

In case esp32 hung
import uos; uos.remove('main.py')

For upload files install ampy: https://github.com/scientifichackers/ampy

#ToDo
 - integrate micropython-mcron into micropython lib 
 - fix COMMAND EXCEPTION
 - make socket server more reliable
 - add support POST request
 - add check for WiFi.waitForConnectResult 
 - set timeout WiFi.setAutoConnect(true) and WiFi.setAutoReconnect(true).

