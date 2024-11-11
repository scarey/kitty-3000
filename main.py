# MIT License (MIT)
# Copyright (c) 2024 Stephen Carey
# https://opensource.org/licenses/MIT

import uasyncio as asyncio
import ujson
from machine import Pin

import Stepper
from mqtt_local import config
from mqtt_as import MQTTClient

VERSION = 3

f = open('config.json')
local_config = f.read()
json = ujson.loads(local_config)
dispenser_num = json['dispenser-num']
max_treats = json['max-treats']
f.close()

IN1 = Pin(json['pin1'], Pin.OUT)
IN2 = Pin(json['pin2'], Pin.OUT)
IN3 = Pin(json['pin3'], Pin.OUT)
IN4 = Pin(json['pin4'], Pin.OUT)

stepper = Stepper.create(IN1, IN2, IN3, IN4, delay=1)
command = 'stop'
treats_remaining = 0
num_dispensed = 0
last_command = None
remote_config = {}

SET_TREAT_COUNT = 'set_treat_count'

BASE_TOPIC = f'esp32/kitty3000/{dispenser_num}'
COMMAND_TOPIC = f'{BASE_TOPIC}/command'
TREATS_TOPIC = f'{BASE_TOPIC}/treats'
CONFIG_TOPIC = f'{BASE_TOPIC}/config'
AVAILABLE_TOPIC = f'{BASE_TOPIC}/availability'


def handle_incoming_message(topic, msg, retained):
    global command, treats_remaining, remote_config
    message_string = msg.decode()
    print("Received `{}` from `{}` topic".format(message_string, topic.decode()))
    if topic == COMMAND_TOPIC:
        command = message_string
    elif topic == TREATS_TOPIC:
        treats_remaining = int(message_string)
    elif topic == CONFIG_TOPIC:
        remote_config = ujson.loads(message_string)


async def wifi_han(state):
    print('Wifi is ', 'up' if state else 'down')
    await asyncio.sleep(1)


# If you connect with clean_session True, must re-subscribe (MQTT spec 3.1.2.4)
async def conn_han(client):
    await client.subscribe(COMMAND_TOPIC, 0)
    await client.subscribe(TREATS_TOPIC, 0)
    await client.subscribe(CONFIG_TOPIC, 0)
    await online()


async def online():
    await client.publish(AVAILABLE_TOPIC, 'online', retain=True, qos=0)


async def main(client):
    await client.connect()
    await asyncio.sleep(2)  # Give broker time
    await online()
    print("Published as online...")
    global remote_config
    while not remote_config:
        print(f"Waiting for MQTT configuration at {CONFIG_TOPIC}...")
        await asyncio.sleep(1)

    try:
        import ha
        print("ha module found, configuring HA discovery.")
        await ha.setup_ha_discovery(client, dispenser_num, remote_config['name'], max_treats, AVAILABLE_TOPIC, VERSION)
    except ImportError:
        print("ha module not found, not configuring HA discovery.")

    global num_dispensed, treats_remaining, command
    while True:
        if command == 'dispense':
            await stepper.angle(30.44)
            num_dispensed += 1
            if num_dispensed == remote_config['adjustment-freq']:
                num_dispensed = 0
                print("Adjusting...")
                await stepper.step(remote_config['adjustment-angle'], direction=-1)
            treats_remaining -= 1
            command = None
            if treats_remaining < 0:
                treats_remaining = 0
            await client.publish(TREATS_TOPIC, str(treats_remaining), retain=True, qos=0)
        elif command == SET_TREAT_COUNT:
            command = None
            await client.publish(TREATS_TOPIC, str(treats_remaining), retain=True, qos=0)
        elif command == 'adjust':
            command = None
            await stepper.angle(remote_config['adjustment-angle'])
        else:
            await asyncio.sleep(0.5)


config['subs_cb'] = handle_incoming_message
config['connect_coro'] = conn_han
config['wifi_coro'] = wifi_han
config['will'] = [AVAILABLE_TOPIC, 'offline', True, 0]

MQTTClient.DEBUG = False
client = MQTTClient(config)
try:
    asyncio.run(main(client))
finally:
    client.close()
    asyncio.new_event_loop()
