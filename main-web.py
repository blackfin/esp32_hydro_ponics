import utime

import mcron

import mcron.decorators

import machine, onewire, ds18x20, time

from machine import Pin

import uasyncio as asyncio

from machine import RTC

import ntptime

from suntime import Sun, SunTimeException

today_sr = None

today_ss = None

cur_temp = None

SetPoint_temp = 30

Fan_prev = 0

rtc = RTC()

Led = Pin(16, Pin.OUT)  # выход на светодиод для индикации работы программы

Lamp = Pin(14, Pin.OUT)  # выход на лампы

ds_pin = Pin(4)  # подключение ds18x20

Fan = Pin(15, Pin.OUT)  # выход на вентилятор


# Моргает для проверки работы программы в целом

async def blink_led(led, interval_ms):
    led_val = True

    while True:
        led_val = not (led_val)

        led_state = led.value(int(led_val))

        await asyncio.sleep_ms(interval_ms)


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

async def read_ds_sensor(
        interval_ms):  # Попробовать переделать с асинхронного режима работы на синхронный - async убрать оставить только мкрон

    while True:
        Read_Sensor_Control_Fan  # print('Read data sensor async')#PrintReadDataSensor

        await asyncio.sleep_ms(interval_ms)


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

        print('Currently temp: ', ds_sensor.read_temp(roms[0]), ', Fan ON, now time : ', rtc.datetime())

    else:

        Fan = 0  # Выключаем вентилятор

        print('Currently temp: ', ds_sensor.read_temp(roms[0]), ', Fan OFF, now time : ', rtc.datetime())

    if Fan != Fan_prev:
        print('Fan status changed, temperature : ', ds_sensor.read_temp(roms[0]), ', now time : ',
              rtc.datetime()[4] + 6, ':', rtc.datetime()[5])

        Fan_prev = Fan

        return Fan_prev


# Включение/выключение  ламп на рассвете

def SunR_Lamp(callback_id, current_time, callback_memory):
    if ((rtc.datetime())[4] + 6 == today_sr[3]) and ((rtc.datetime())[5] == today_sr[4]):

        print('SunRise lamp ON in  : ', rtc.datetime()[4] + 6, ':', rtc.datetime()[5], 'Sunrise today ', today_sr[3],
              ':', today_sr[4])

    else:

        print('SunRise lamp OFF in  : ', rtc.datetime()[4] + 6, ':', rtc.datetime()[5], 'Sunrise today ', today_sr[3],
              ':', today_sr[4])


# Включение/выключение  ламп на закате

def SunS_Lamp(callback_id, current_time, callback_memory):
    if ((rtc.datetime())[4] + 6 == today_ss[3]) and ((rtc.datetime())[5] == today_ss[4]):

        print('SunSet lamp OFF in  : ', rtc.datetime()[4] + 6, ':', rtc.datetime()[5], 'SunSet today ', today_ss[3],
              ':', today_ss[4])

    else:

        print('SunSet lamp ON in  : ', rtc.datetime()[4] + 6, ':', rtc.datetime()[5], 'SunSet today ', today_ss[3], ':',
              today_ss[4])


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

    #        Read_Sensor()

    elif request.find('GET /?onlamp') > 0:

        Lamp_state = "on lamp"

        auto_run_flag = False

    #        Read_Sensor()

    elif request.find('GET /?offfan') > 0:

        Fan_state = "off fan"

        auto_run_flag = False

    #        Read_Sensor()

    elif request.find('GET /?onfan') > 0:

        Fan_state = "on fan"

        auto_run_flag = False

    #        Read_Sensor()

    elif request.find('POST /set_point_temp') > 0:

        headers = request.split('\n')

        set_point = request.get("temp", "")

        fan_state = str(set_point)

        print("Set_point_value = ", set_point)

    #        auto_run_flag = False

    html = """<html><head><title>Hydroponic WEB</title>

    <meta name="viewport" content="width=device-width, initial-scale=1">

    <link rel="icon" href="data:,"> <style>

    html{font-family: Helvetica; display:inline-block; margin: 0px auto; text-align: center;}

    h1{color: #0F3376; padding: 2vh;}p{font-size: 1.5rem;}

    .button{display: inline-block; background-color: #33c080; border: none;

    border-radius: 4px; color: white; text-decoration: none; font-size: 30px; width:100%}

    .button2{background-color: #4286f4; width:30%}

    .button3{background-color: #eb2b10; width:30%}

    .button4{background-color: #8386f4; width:44%}

    </style></head>

    <body> <h1>Hydroponic</h1>

    <p>Currently temperature : <strong>""" + str(cur_temp) + """</strong></p>

    <p>Status Lamp : <strong>""" + Lamp_state + """</strong></p>

    <p>Status Fan : <strong>""" + Fan_state + """</strong></p>

    <p>Today SunRise : <strong>""" + str(today_sr[3]) + """:""" + str(today_sr[4]) + """</strong></p>

    <p>Today SunSet : <strong>""" + str(today_ss[3]) + """:""" + str(today_ss[4]) + """</strong></p>

    <p>SetPoint temperature : <strong>""" + str(SetPoint_temp) + """</strong></p>

    <form action="/set_point_temp"  method="post">

        <label for="SetPoint_temp">Set Point temperature:</label><br>

        <input type="number" id="SetPoint_temp" name="temp" value=""" + str(SetPoint_temp) + """ /><br><br>

        <input type="submit" value="Submit">

    </form>

    <p><a href='/?offlamp'><button class="button button2">OFF Lamp</button></a>

    <a href='/?onlamp'><button class="button button3">ON Lamp</button></a></p>

    <p><a href='/?offfan'><button class="button button2">OFF Fan</button></a>

    <a href='/?onfan'><button class="button button3">ON Fan</button></a></p>



    </body></html>"""

    return html


async def web_handler(reader, writer):
    try:

        request = str(await reader.read(1024))

        print('request = %s' % request)

        header = """HTTP/1.1 200 OK\nContent-Type: text/html\nConnection: close\n\n"""

        response = await web_page(request)

        await writer.awrite(header)

        await writer.awrite(response)

        await writer.aclose()

        print("Finished processing request")

    except Exception as e:

        print(e)


async def tcp_server(host, port):
    server = await asyncio.start_server(web_handler, host, port)


Sync_Time(1, 2, 3)

mcron.init_timer()

loop = asyncio.get_event_loop()

# create looped tasks

loop.create_task(blink_led(Led, interval_ms=250))

loop.create_task(read_ds_sensor(interval_ms=60000))

loop.create_task(SunRise_Lamp())

loop.create_task(SunSet_Lamp())

loop.create_task(syncr_time())

loop.create_task(tcp_server('0.0.0.0', 80))

loop.run_forever()

loop.close()
