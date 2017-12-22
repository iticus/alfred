'''
Created on Dec 16, 2017

@author: ionut
'''

import dht
import machine
import uasyncio as asyncio

sensor = dht.DHT22(machine.Pin(12))

@asyncio.coroutine
def measure():
    while True:
        await asyncio.sleep(3)
        try:
            sensor.measure()
        except:
            pass

@asyncio.coroutine
def serve(reader, writer):
    request = await reader.read()
    response = "HTTP/1.0 200 OK\r\n\r\n"
    value = "%s,%s" % (sensor.temperature(), sensor.humidity())
    await writer.awrite(response + value)
    await writer.aclose()

loop = asyncio.get_event_loop()
loop.call_soon(measure())
loop.call_soon(asyncio.start_server(serve, "0.0.0.0", 8080))
loop.run_forever()
loop.close()
