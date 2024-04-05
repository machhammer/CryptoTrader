import time
import paho.mqtt.client as mqtt


def on_connect(client, userdata, flags, rc, properties=None):
    print("CONNACK received with code %s." % rc)


def on_message(client, userdata, msg):
    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))



client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set("machhammer@gmx.net", "Mdd.CyCGSibB33q")

client.on_connect = on_connect
client.connect("0f8e8cf45e56466c80e26d7ce54a1975.s1.eu.hivemq.cloud", 8883)

client.subscribe("test", qos=1)

client.publish("test", payload="hot", qos=1)

client.loop_forever()