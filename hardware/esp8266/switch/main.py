"""
Created on Dec 16, 2017

@author: ionut
"""

import machine
import uasyncio as asyncio

pin = machine.Pin(13, machine.Pin.OUT)

@asyncio.coroutine
def serve(reader, writer):
    request = yield from reader.read()
    response = "HTTP/1.0 200 OK\r\n\r\n"
    if "POST /turn_on " in request:
        pin.on()
        yield from writer.awrite(response + "OK")
    elif "POST /turn_off " in request:
        pin.off()
        yield from writer.awrite(response + "OK")
    else:
        value = "%s" % (pin.value())
        yield from writer.awrite(response + value)
    yield from writer.aclose()

loop = asyncio.get_event_loop()
loop.call_soon(asyncio.start_server(serve, "0.0.0.0", 8080))
loop.run_forever()
loop.close()
