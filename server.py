#!/usr/bin/python
import minimalmodbus
import serial
import sys  
import re
import time
import json

from paho.mqtt.client import Client

mqtt_broker = '192.168.6.46'
mqtt_user = 'emonpi'
mqtt_pass = 'emonpimqtt2016'
mqtt_port = 1883

modbus_port = "/dev/ttyUSB0"
modbus_id = 1

solis1500 = minimalmodbus.Instrument(modbus_port, modbus_id, debug = False, close_port_after_each_call = True)

### Solis 1500 Registers

### All registers use function code 4

SOLIS1500_REG_ACWATTS =   3004  # Read AC Watts as Unsigned 32-Bit
SOLIS1500_REG_DCVOLTS =   3021  # Read DC Volts as Unsigned 16-Bit
SOLIS1500_REG_DCCURRENT = 3022  # Read DC Current as Unsigned 16-Bit
SOLIS1500_REG_ACVOLTS =   3035  # Read AC Volts as Unsigned 16-Bit
SOLIS1500_REG_ACCURRENT = 3038  # Read AC Current as Unsigned 16-Bit
SOLIS1500_REG_ACFREQ =    3042  # Read AC Frequency as Unsigned 16-Bit
SOLIS1500_REG_ALLTIMEKW = 3008  # Read All Time Energy (KWH Total) as Unsigned 32-Bit
SOLIS1500_REG_TODAYKW =   3014  # Read Today Energy (KWH Total) as 16-Bit

node_name = "gridsolar"
topic_base = "homeassistant/sensor/" + node_name

Solis1500 = {}
Solis1500['AlltimeEnergy_KW_z'] = 0
Solis1500['Today_KW_z'] = 0
Solis1500['ACW'] = 0
Solis1500['DCV'] = 0
Solis1500['DCI'] = 0
Solis1500['ACV'] = 0
Solis1500['ACI'] = 0
Solis1500['ACF'] = 0
Solis1500['Temp'] = 0

solis1500 = minimalmodbus.Instrument(modbus_port, modbus_id, debug = False, close_port_after_each_call = True)

client = Client("ginlong")
client.username_pw_set(mqtt_user, mqtt_pass)
client.connect("192.168.6.46", 1883)
client.loop_start()


def publish_config(unit, type, name, state):
    payload = json.loads('{}')
    payload["unit_of_measurement"] = unit
    payload["device_class"] = type
    payload["name"] = node_name + "_" + name
    payload["unique_id"] = name + "1"
    payload["state_topic"] = topic_base + "/state"
    payload["availability_topic"] = topic_base + "/available"
    payload["value_template"] = "{{ value_json." + name + " }}"
    payload["state_class"] = state

    client.publish(topic=topic_base + "/" + name + "/config", payload=json.dumps(payload), qos=0, retain=True)


def get_readings():

    try:
        Solis1500['AlltimeEnergy_KW_z'] = solis1500.read_long(3008, functioncode=4, signed=False) # Read All Time Energy (KWH Total) as Unsigned 32-Bit
        Solis1500['Today_KW_z'] = solis1500.read_register(3014, number_of_decimals=1, functioncode=4, signed=False) # Read Today Energy (KWH Total) as 16-Bit
        Solis1500['ACW'] = solis1500.read_long(3004, functioncode=4, signed=False) # Read AC Watts as Unsigned 32-Bit
        Solis1500['DCV'] = solis1500.read_register(3021, number_of_decimals=1, functioncode=4, signed=False) # Read DC Volts as Unsigned 16-Bit
        Solis1500['DCI'] = solis1500.read_register(3022, number_of_decimals=0, functioncode=4, signed=False) # Read DC Current as Unsigned 16-Bit
        Solis1500['ACV'] = solis1500.read_register(3035, number_of_decimals=1, functioncode=4, signed=False) # Read AC Volts as Unsigned 16-Bit
        Solis1500['ACI'] = solis1500.read_register(3038, number_of_decimals=0, functioncode=4, signed=False) # Read AC Current as Unsigned 16-Bit
        Solis1500['ACF'] = solis1500.read_register(3042, number_of_decimals=2, functioncode=4, signed=False) # Read AC Frequency as Unsigned 16-Bit
        Solis1500['Temp'] = solis1500.read_register(3041, number_of_decimals=1, functioncode=4, signed=True) # Read Inverter Temperature as Signed 16-Bit

        year = solis1500.read_register(3072, number_of_decimals=0, functioncode=4, signed=False) 
        month = solis1500.read_register(3073, number_of_decimals=0, functioncode=4, signed=False)
        day = solis1500.read_register(3074, number_of_decimals=0, functioncode=4, signed=False)
        hour = solis1500.read_register(3075, number_of_decimals=0, functioncode=4, signed=False)
        minute = solis1500.read_register(3076, number_of_decimals=0, functioncode=4, signed=False)
        seconds = solis1500.read_register(3077, number_of_decimals=0, functioncode=4, signed=False)

        payload = json.loads('{}')
        payload['total_energy'] = str(Solis1500['AlltimeEnergy_KW_z'])
        payload['today_energy'] = str(Solis1500['Today_KW_z'])
        payload['current_power'] = str(Solis1500['ACW'])
        payload['dc_voltage'] = str(Solis1500['DCV'])
        payload['dc_current'] = str(Solis1500['DCI'])
        payload['ac_voltage'] = str(Solis1500['ACV'])
        payload['ac_current'] = str(Solis1500['ACI'])
        payload['ac_frequency'] = str(Solis1500['ACF'])
        payload['temperature'] = str(Solis1500['Temp'])

        print(payload)
        if Solis1500['AlltimeEnergy_KW_z'] != 0:
            client.publish(topic=topic_base + "/state", payload=json.dumps(payload), qos=0, retain=False)
        else:
            print("Total energy is 0, something is wrong. Not sending")

    except Exception as e:
        print(f"Offline.......................{e}")


def main():

    solis1500.serial.baudrate = 9600   # Baud
    solis1500.serial.bytesize = 8
    solis1500.serial.parity   = serial.PARITY_NONE
    solis1500.serial.stopbits = 1
    solis1500.clear_buffers_before_each_transaction = True
    solis1500.serial.timeout  = 0.5   # seconds
    solis1500.mode = minimalmodbus.MODE_RTU

    publish_config("kWh", "energy", "total_energy", "total_increasing")
    publish_config("kWh", "energy", "today_energy", "total_increasing")
    publish_config("W", "power", "current_power", "measurement")
    publish_config("V", "voltage", "dc_voltage", "measurement")
    publish_config("A", "current", "dc_current", "measurement")
    publish_config("V", "voltage", "ac_voltage", "measurement")
    publish_config("A", "current", "ac_current", "measurement")
    publish_config("Hz", "frequency", "ac_frequency", "measurement")
    publish_config("°C", "temperature", "temperature", "measurement")

    while True:
        get_readings()

        client.publish(topic=topic_base + "/available", payload="online", qos=0, retain=False)

        time.sleep(10)


if __name__ == "__main__":
    main()

