# esp32_hydro_ponics

On host PC:
```
sudo adduser myusername dialout (requires reboot)
sudo apt-get install picocom

sudo apt-get install python3-pip
pip3 install esptool
pip3 install pyserial

sudo usermod -a -G tty yourname
```
Erase flash on board. In host PC terminal execute
```
esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash
```
In terminal should see:
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

Flashing micropython firmware starting at address 0x1000:
```
esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x1000 esp32-20190125-v1.10.bin
```
Ok, the board is prepare.
For upload files install ampy: https://github.com/scientifichackers/ampy
```
ampy --port /dev/ttyUSB0 put board_boot.py /boot.py
ampy --port /dev/ttyUSB0 put ./src/main.py  /main.py
```
More info: https://learn.adafruit.com/micropython-basics-load-files-and-run-code/file-operations

In case esp32 hung or not responded thru web interface:
```
picocom -b 115200 /dev/ttyUSB0
```
use CTRL-C to break, CTRL-D for soft reboot. Go to REPL and execute:
```
import uos; uos.remove('main.py')
```
Fix main.py and reupload.

#ToDo
 - fix COMMAND EXCEPTION
 - add check for WiFi.waitForConnectResult 
 - set timeout WiFi.setAutoConnect(true) and WiFi.setAutoReconnect(true).

