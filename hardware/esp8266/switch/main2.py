'''
Created on Dec 16, 2017

@author: ionut
'''

import machine
import uasyncio as asyncio

pin1 = machine.Pin(12, machine.Pin.OUT)
pin2 = machine.Pin(13, machine.Pin.OUT)

@asyncio.coroutine
def serve(reader, writer):
    request = yield from reader.read()
    response = "HTTP/1.0 200 OK\r\n\r\n"
    if 'POST /turn_on ' in request:
        pin1.on()
        await asyncio.sleep_ms(100)
        pin2.on()
        yield from writer.awrite(response + 'OK')
    elif 'POST /turn_off ' in request:
        pin1.off()
        await asyncio.sleep_ms(100)
        pin2.off() 
        yield from writer.awrite(response + 'OK')
    else:
        value = "%s,%s" % (pin1.value(), pin2.value())
        yield from writer.awrite(response + value)
    yield from writer.aclose()

loop = asyncio.get_event_loop()
loop.call_soon(asyncio.start_server(serve, "0.0.0.0", 8080))
loop.run_forever()
loop.close()
