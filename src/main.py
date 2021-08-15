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
import re
import gc
import micropython

today_sr = None
today_ss = None
cur_temp = None
set_point_temp = 30
Fan_prev = 0
rtc = RTC()
Lamp = Pin(14, Pin.OUT)  # выход на лампы
ds_pin = Pin(4)  # подключение ds18x20
Fan = Pin(15, Pin.OUT)  # выход на вентилятор
led = Pin(2, Pin.OUT)  # выход на светодиод для индикации работы программы
SEND_BUFSZ = 128
lamp_state = "OFF"
fan_state = "OFF"
global auto_run_flag, nSP


async def killer(duration):
    await asyncio.sleep(duration)


async def toggle(ledfortoggle, time_ms):
    led_val = True
    while True:
        await asyncio.sleep_ms(time_ms)
        led_val = not led_val
        led_state = ledfortoggle.value(int(led_val))


async def main(duration, blinked):
    print("Flash LED's for {} seconds".format(duration))
    asyncio.create_task(toggle(blinked, int((0.2 + 1 / 2) * 1000)))
    asyncio.run(killer(duration))


# Взятие времени с ntp сервера, парсинг данных
def sync_time(callback_id, current_time, callback_memory):
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


def Read_Sensor():
    global cur_temp

    ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))
    roms = ds_sensor.scan()
    ds_sensor.convert_temp()
    #    print ('Currently temp: ', ds_sensor.read_temp(roms[0]))
    cur_temp = ds_sensor.read_temp(roms[0])


def handle(reader, writer):
    # micropython.mem_info()
    close = True
    try:
        request_line = yield from reader.readline()

        if request_line == b"":
            yield from writer.aclose()
            return

        request_line = request_line.decode()
        method, path, proto = request_line.split()

        headers = yield from parse_headers(reader)

        if b"Content-Length" in headers:
            size = int(headers[b"Content-Length"])
        else:
            size = 0

        if len(path) > 1:
            data = yield from reader.readexactly(size)
            form = parse_qs(data.decode())
        else:
            data = b''
            form = {}

        path = path.split("?", 1)
        qs = ""
        if len(path) > 1:
            qs = path[1]
        path = path[0]
        print('%.3f %s %s "%s %s" "%s %s %s"' % (utime.time(), headers, size, data, form, method, path, qs))
        print("method %s", method)
        if method == "POST":
            yield from start_response(writer)
            yield from writer.awrite(web_page())
            set_point_temp = form["temp"]  # temperature from POST request
            print("Temperature for setting:", set_point_temp)
            fan_state = str(set_point_temp)
            auto_run_flag = False
            Read_Sensor()
        else:  # GET, apparently
            # Note: parse_qs() is not a coroutine, but a normal function.
            # But you can call it using yield from too.
            print("request path %s", path)
            if not qs:
                yield from start_response(writer, status="200")
                yield from writer.awrite(web_page())
                return

            print("query string %s", qs)
            if qs == 'offlamp':
                lamp_state = "off lamp"
                auto_run_flag = False
                Read_Sensor()
            elif qs == 'onlamp':
                lamp_state = "on lamp"
                auto_run_flag = False
                Read_Sensor()
            elif qs == 'offfan':
                fan_state = "off fan"
                auto_run_flag = False
                Read_Sensor()
            elif qs == 'onfan':
                fan_state = "on fan"
                auto_run_flag = False
                Read_Sensor()
            print("settings %s %s %s", fan_state, auto_run_flag, lamp_state)
            yield from start_response(writer, status="200")
            yield from writer.awrite(web_page())
    except Exception as e:
        print("Error", e.__class__, "occurred.")

    if close is not False:
        yield from writer.aclose()


def parse_headers(reader):
    headers = {}
    while True:
        l = yield from reader.readline()
        if l == b"\r\n":
            break
        k, v = l.split(b":", 1)
        headers[k] = v.strip()
    return headers


def unquote_plus(s):
    # TODO: optimize
    s = s.replace("+", " ")
    arr = s.split("%")
    arr2 = [chr(int(x[:2], 16)) + x[2:] for x in arr[1:]]
    return arr[0] + "".join(arr2)


def parse_qs(s):
    res = {}
    if s:
        pairs = s.split("&")
        for p in pairs:
            vals = [unquote_plus(x) for x in p.split("=", 1)]
            if len(vals) == 1:
                vals.append(True)
            old = res.get(vals[0])
            if old is not None:
                if not isinstance(old, list):
                    old = [old]
                    res[vals[0]] = old
                old.append(vals[1])
            else:
                res[vals[0]] = vals[1]
    return res


def start_response(writer, content_type="text/html; charset=utf-8", status="200", headers=None):
    print("Start response to browser")
    yield from writer.awrite("HTTP/1.0 %s NA\r\n" % status)
    yield from writer.awrite("Content-Type: ")
    yield from writer.awrite(content_type)
    if not headers:
        yield from writer.awrite("\r\n\r\n")
        return
    yield from writer.awrite("\r\n")
    if isinstance(headers, bytes) or isinstance(headers, str):
        yield from writer.awrite(headers)
    else:
        for k, v in headers.items():
            yield from writer.awrite(k)
            yield from writer.awrite(": ")
            yield from writer.awrite(v)
            yield from writer.awrite("\r\n")
    yield from writer.awrite("\r\n")


def web_page():
    html = b"""
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
    <p>Status Lamp : <strong>""" + lamp_state + """</strong></p>
    <p>Status Fan : <strong>""" + fan_state + """</strong></p>
    <p>Today SunRise : <strong>""" + str(today_sr[3]) + """:""" + str(2) + """</strong></p>
    <p>Today SunSet : <strong>""" + str(today_ss[3]) + """:""" + str(4) + """</strong></p>
    <p>SetPoint temperature : <strong>""" + str(set_point_temp) + """</strong></p>

    <form action="/set_point_temp"  method="POST">
        <label for="set_point_temp">Set Point temperature:</label><br>
        <input type="number" id="set_point_temp" name="temp" value=""" + str(set_point_temp) + """ /><br><br>
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
    # create looped tasks
    gc.collect()
    sync_time(1, 2, 3)
    mcron.init_timer()
    try:
        loop = asyncio.get_event_loop()
        # loop.create_task(main(duration, led))  # Запланировать как можно скорее
        loop.create_task(
            asyncio.start_server(handle, ip, 80)
        )
        loop.run_forever()  # loop run forever
    except KeyboardInterrupt:
        print('Interrupted')
        loop.close()
    except Exception as e:
        print("Error", e.__class__, "occurred.")
        print("Next entry.")
        print()
        loop.close()
    finally:
        asyncio.new_event_loop()
        print('test() to run again.')


if __name__ == '__main__':
    test()
    # do_connect()
