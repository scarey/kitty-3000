# MIT License (MIT)
# Copyright (c) 2024 Stephen Carey
# https://opensource.org/licenses/MIT

# OTA:file:ha.py
# OTA:reboot:true
import binascii
import json
import uos
from machine import unique_id

from mqtt_as import MQTTClient


async def setup_ha_discovery(client: MQTTClient, dispenser_num, name, max_treats, available_topic, version):
    identifier = binascii.hexlify(unique_id()).decode()
    device = {
        "identifiers": identifier,
        "name": name,
        "sw_version": f"{uos.uname().version}_{version}",
        "model": uos.uname().machine,
        "manufacturer": identifier
    }

    topic = f"homeassistant/number/kitty3000-{dispenser_num}/treats/config"
    message = {
        "name": "Treats remaining",
        "availability_topic": available_topic,
        "qos": 0,
        # "icon": "mdi:react",
        "device": device,
        "state_topic": f"esp32/kitty3000/{dispenser_num}/treats",
        "command_topic": f"esp32/kitty3000/{dispenser_num}/treats",
        "min": 0,
        "max": max_treats,
        "mode": "slider",
        "retain": True,
        "state_class": "TOTAL",
        "unique_id": f"kitty3000-{dispenser_num}-treats",
        'force_update': True
    }
    await client.publish(topic, json.dumps(message).encode("UTF-8"), True)

    my_unique_id = f"kitty3000-{dispenser_num}-dispense"
    topic = f"homeassistant/button/{my_unique_id}/config"
    message = {
        "name": "Dispense",
        "availability_topic": available_topic,
        "qos": 0,
        # "icon": "mdi:ruler-square-compass",
        "device": device,
        "command_topic": f"esp32/kitty3000/{dispenser_num}/command",
        "payload_press": "dispense",
        "unique_id": my_unique_id
    }
    await client.publish(topic, json.dumps(message).encode("UTF-8"), True)

    my_unique_id = f"kitty3000-{dispenser_num}-adjust"
    topic = f"homeassistant/button/{my_unique_id}/config"
    message = {
        "name": "Adjust",
        "availability_topic": available_topic,
        "qos": 0,
        # "icon": "mdi:ruler-square-compass",
        "device": device,
        "command_topic": f"esp32/kitty3000/{dispenser_num}/command",
        "payload_press": "adjust",
        "unique_id": my_unique_id
    }
    await client.publish(topic, json.dumps(message).encode("UTF-8"), True)
