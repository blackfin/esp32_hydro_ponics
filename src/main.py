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

led = Pin(2, Pin.OUT)  # выход на светодиод для индикации работы программы
SEND_BUFSZ = 128


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


def handle(reader, writer):
    # micropython.mem_info()
    close = True
    req = None
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

        data = yield from reader.readexactly(size)

        form = parse_qs(data.decode())

        path = path.split("?", 1)
        qs = ""
        if len(path) > 1:
            qs = path[1]
        path = path[0]
        print('%.3f %s %s "%s %s" "%s %s"' % (utime.time(), headers, size, data, form, method, path))
        if method == "POST":
            print("method %s", method)
            yield from start_response(writer)
            yield from writer.awrite(web_page())
            temp = form["temp"]
            print("Temperature for setting:", temp)

        else:  # GET, apparently
            # Note: parse_qs() is not a coroutine, but a normal function.
            # But you can call it using yield from too.
            print("method %s", method)
            yield from start_response(writer, status="200")
            #yield from writer.awrite("404\r\n")
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
    <p>Currently temperature : <strong>""" + str(22) + """</strong></p>
    <p>Status Lamp : <strong>""" + "Off" + """</strong></p>
    <p>Status Fan : <strong>""" + "Off" + """</strong></p>
    <p>Today SunRise : <strong>""" + str(1) + """:""" + str(2) + """</strong></p>
    <p>Today SunSet : <strong>""" + str(3) + """:""" + str(4) + """</strong></p>
    <p>SetPoint temperature : <strong>""" + str(15) + """</strong></p>

    <form action="/set_point_temp"  method="POST">
        <label for="set_point_temp">Set Point temperature:</label><br>
        <input type="number" id="set_point_temp" name="temp" value=""" + str(15) + """ /><br><br>
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
