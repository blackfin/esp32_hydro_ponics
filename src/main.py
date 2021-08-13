import utime, network
import mcron
import mcron.decorators
import machine, onewire, ds18x20, time
from machine import Pin
import uasyncio as asyncio
from machine import RTC
import ntptime
from suntime import Sun, SunTimeException
import socket
import sys

today_sr = None
today_ss = None
cur_temp = None
SetPoint_temp = 30
Fan_prev = 0
rtc = RTC()
Lamp = Pin(14, Pin.OUT)  # выход на лампы
ds_pin = Pin(4)  # подключение ds18x20
Fan = Pin(15, Pin.OUT)  # выход на вентилятор
led = Pin(2, Pin.OUT)  # выход на светодиод для индикации работы программы


# Запускаем 2 раза в день для включения/выключения ламп при рассвете и переход на подпрограмму SunR_Lamp
async def SunRise_Lamp():
    mcron.insert(mcron.PERIOD_DAY, {0 * 60 * 60 + 30 * 60, today_sr[3] * 60 * 60 + today_sr[4] * 60},
                 'SunRise_6_30_today_sr', SunR_Lamp)
    await asyncio.sleep_ms(1000)


# Запускаем 2 раза в день для включения/выключения ламп при закате и переход на подпрограмму SunS_Lamp
async def SunSet_Lamp():
    mcron.insert(mcron.PERIOD_DAY, {today_ss[3] * 60 * 60 + today_ss[4] * 60, 15 * 60 * 60 + 30 * 60},
                 'SunSet_21_30_today_ss', SunS_Lamp)
    await asyncio.sleep_ms(3000)


# Запускаем подпрограмму чтения данных о температуре каждую минуту переход на подпрограмму Read_Sensor_Control_Fan
async def read_ds_sensor1():
    mcron.insert(mcron.PERIOD_MINUTE, range(0, mcron.PERIOD_MINUTE, 60), '1 minute', Read_Sensor_Control_Fan)
    await asyncio.sleep(750)


# Синхронизация времени 2 раза в день 00:30 и 12:30 отправка на подпрограмму Sync_Time
async def syncr_time():
    mcron.insert(mcron.PERIOD_DAY, {6 * 60 * 60 + 30 * 60, 21 * 60 * 60 + 30 * 60}, '00:30 syncronisation time',
                 Sync_Time)
    await asyncio.sleep(2000)


# Взятие времени с ntp сервера, парсинг данных
def Sync_Time(callback_id, current_time, callback_memory):
    ntptime.settime()  # set the rtc datetime from the remote server
    rtc.datetime()  # get the date and time in UTC
    global today_sr, today_ss
    latitude = 54.58  # Установка широты для Омска
    longitude = 73.23  # Установка долготы для Омска
    sun = Sun(latitude, longitude, 6)  # Вычисление солнца с учетом +6 пояса
    # Get today's sunrise and sunset in UTC
    today_sr = sun.get_sunrise_time()
    today_ss = sun.get_sunset_time()
    print("Time synchronization was successful! Sunrise today %s:%s, sunset today %s:%s" % (
        today_sr[3], today_sr[4], today_ss[3], today_ss[4]))
    return today_sr, today_ss


# Получение данных о температуре и включение вентилятора
def Read_Sensor_Control_Fan(callback_id, current_time, callback_memory):
    global Fan_prev, SetPoint_temp
    ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))
    roms = ds_sensor.scan()
    ds_sensor.convert_temp()
    if (ds_sensor.read_temp(roms[0])) > SetPoint_temp:  # Если температура выше 30 град
        Fan = 1  # Включаем вентилятор
    #        print ('Currently temp: ', ds_sensor.read_temp(roms[0]), ', Fan ON, now time : ', rtc.datetime())
    else:
        Fan = 0  # Выключаем вентилятор
    #        print ('Currently temp: ', ds_sensor.read_temp(roms[0]), ', Fan OFF, now time : ', rtc.datetime())
    if Fan != Fan_prev:
        print('Fan status changed, temperature : ', ds_sensor.read_temp(roms[0]), ', now time : ',
              rtc.datetime()[4] + 6, ':', rtc.datetime()[5])
        Fan_prev = Fan
        return Fan_prev


# Включение/выключение  ламп на рассвете
def SunR_Lamp(callback_id, current_time, callback_memory):
    if ((rtc.datetime())[4] + 6 == today_sr[3]) and ((rtc.datetime())[5] == today_sr[4]):
        print('SunRise lamp ON in  : ', rtc.datetime(), 'Sunrise today ', today_sr[3], ':', today_sr[4])
    else:
        print('SunRise lamp OFF in  : ', rtc.datetime(), 'Sunrise today ', today_sr[3], ':', today_sr[4])


# Включение/выключение  ламп на закате
def SunS_Lamp(callback_id, current_time, callback_memory):
    if ((rtc.datetime())[4] + 6 == today_ss[3]) and ((rtc.datetime())[5] == today_ss[4]):
        print('SunSet lamp OFF in  : ', rtc.datetime(), 'SunSet today ', today_ss[3], ':', today_ss[4])
    else:
        print('SunSet lamp ON in  : ', rtc.datetime(), 'SunSet today ', today_ss[3], ':', today_ss[4])


def Read_Sensor():
    global cur_temp
    ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))
    roms = ds_sensor.scan()
    ds_sensor.convert_temp()
    #    print ('Currently temp: ', ds_sensor.read_temp(roms[0]))
    cur_temp = ds_sensor.read_temp(roms[0])


async def web_page(request):
    global auto_run_flag, nSP
    Lamp_state = "OFF"
    Fan_state = "OFF"
    if request.find('GET /?offlamp') > 0:
        Lamp_state = "off lamp"
        auto_run_flag = False
        Read_Sensor()
    elif request.find('GET /?onlamp') > 0:
        Lamp_state = "on lamp"
        auto_run_flag = False
        Read_Sensor()
    elif request.find('GET /?offfan') > 0:
        Fan_state = "off fan"
        auto_run_flag = False
        Read_Sensor()
    elif request.find('GET /?onfan') > 0:
        Fan_state = "on fan"
        auto_run_flag = False
        Read_Sensor()
    elif request.find('POST /set_point_temp') > 0:
        set_point = request.form.get("temp", "")
        fan_state = str(set_point)
        print("Fan_state", set_point)
        auto_run_flag = False
        Read_Sensor()

    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <title>Hydroponic WEB</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="icon" href="data:,">
    <style>
        html {
            font-family: Helvetica;
            display: inline-block;
            margin: 0px auto;
            text-align: center;
        }

        h1 {
            color: #0F3376;
            padding: 2vh;
        }

        p {
            font-size: 1.5rem;
        }

        .button {
            display: inline-block;
            background-color: #33c080;
            border: none;
            border-radius: 4px;
            color: white;
            text-decoration: none;
            font-size: 30px;
            width: 100%
        }

        .button2 {
            background-color: #4286f4;
            width: 30%
        }

        .button3 {
            background-color: #eb2b10;
            width: 30%
        }

        .button4 {
            background-color: #8386f4;
            width: 44%
        }
    </style>
    </head>
    <body>
    <h1>Hydroponic</h1>
    <p>Currently temperature : <strong>""" + str(cur_temp) + """</strong></p>
    <p>Status Lamp : <strong>""" + Lamp_state + """</strong></p>
    <p>Status Fan : <strong>""" + Fan_state + """</strong></p>
    <p>Today SunRise : <strong>""" + str(today_sr[3]) + """:""" + str(today_sr[4]) + """</strong></p>
    <p>Today SunSet : <strong>""" + str(today_ss[3]) + """:""" + str(today_ss[4]) + """</strong></p>
    <p>SetPoint temperature : <strong>""" + str(SetPoint_temp) + """</strong></p>

    <form action="/set_point_temp"  method="POST">
        <label for="set_point_temp">Set Point temperature:</label><br>
        <input type="number" id="set_point_temp" name="temp" value=""" + str(SetPoint_temp) + """ /><br><br>
        <input type="submit" value="Submit">
    </form>
    <br>
    <p>
        <input class="button button2" type="button" value="OFF Lamp" onclick="location.href='/?offlamp';">
        <input class="button button3" type="button" value="ON Lamp" onclick="location.href='/?onlamp';">
    </p>
    <p>
        <input class="button button2" type="button" value="OFF Fan" onclick="location.href='/?offfan';">
        <input class="button button3" type="button" value="ON Fan" onclick="location.href='/?onfan';">
    </p>
    </body>
    </html>"""
    return html


async def do_connect(ip):
    addr = socket.getaddrinfo(ip, 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    # number of connections
    s.listen(5)
    print('listening on', addr)
    while True:
        conn, addr = s.accept()
        print("Got connection from %s" % str(addr))
        # Socket receive()
        request = conn.recv(1024)
        print("")
        print("")
        print("Content %s" % str(request))

        # Socket send()
        request = str(request)
        # led_on = request.find('/?LED=1')
        # led_off = request.find('/?LED=0')

        # if led_on > 0:
        #    print('LED ON')
        #    print(str(led_on))
        #    led.value(1)
        # elif led_off > 0:
        #    print('LED OFF')
        #    print(str(led_off))
        #   led.value(0)

        response = await web_page(request)
        conn.send('HTTP/1.1 200 OK\n')
        conn.send('Content-Type: text/html\n')
        conn.send('Connection: close\n\n')
        conn.sendall(response)

        # Socket close()
        conn.close()


async def web_page_led(led):
    if led.value() == 1:
        led_state = 'ON'
        print('led is ON')
    elif led.value() == 0:
        led_state = 'OFF'
        print('led is OFF')

    html_page = """    
    <html>    
    <head>    
     <meta content="width=device-width, initial-scale=1" name="viewport"></meta>    
    </head>    
    <body>    
     <center><h2>ESP32 blink demo </h2></center>    
     <center>    
      <form>    
      <button name="LED" type="submit" value="1"> LED ON </button>    
      <button name="LED" type="submit" value="0"> LED OFF </button>  
      </form>    
     </center>    
     <center><p>LED is now <strong>""" + led_state + """</strong>.</p></center>    
    </body>    
    </html>"""
    return html_page


async def killer(duration):
    await asyncio.sleep(duration)


async def toggle(led, time_ms):
    led_val = True
    while True:
        await asyncio.sleep_ms(time_ms)
        led_val = not led_val
        led_state = led.value(int(led_val))


async def main(duration, blinkedLed):
    print("Flash LED's for {} seconds".format(duration))
    asyncio.create_task(toggle(blinkedLed, int((0.2 + 1 / 2) * 1000)))
    asyncio.run(killer(duration))


def test(duration=10):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect("t0mcruzz", "RvM@55#2891")
        while not wlan.isconnected():
            pass
    print('network config for main:', wlan.ifconfig())
    ip = wlan.ifconfig()[0]
    print('ip:', ip)
    Sync_Time(1, 2, 3)
    mcron.init_timer()
    # create looped tasks
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(main(duration, led))  # Запланировать как можно скорее
        loop.create_task(SunRise_Lamp())
        loop.create_task(SunSet_Lamp())
        loop.create_task(read_ds_sensor1())
        loop.create_task(syncr_time())
        loop.create_task(do_connect(ip))
        loop.run_forever()  # loop run forever
        loop.close()
    except KeyboardInterrupt:
        print('Interrupted')
    except Exception as e:
        print("Error", e.__class__, "occurred.")
        print("Next entry.")
        print()
    finally:
        asyncio.new_event_loop()
        print('test() to run again.')


if __name__ == '__main__':
    test()
    # do_connect()
