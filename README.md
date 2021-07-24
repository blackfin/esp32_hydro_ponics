# esp32_hydro_ponics
sudo apt-get install python3-pip
pip3 install esptool
pip3 install pyserial

sudo usermod -a -G tty yourname

esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash

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
