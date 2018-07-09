from __future__ import print_function
from is_wire.core import Channel, Subscription, Message
from is_msgs.camera_pb2 import CameraConfig, CameraConfigFields
from is_msgs.image_pb2 import ColorSpaces
from is_msgs.common_pb2 import FieldSelector
import sys

channel = Channel("amqp://10.10.2.20:30000")
subscription = Subscription(channel)


def on_set_config(msg, ctx):
    print(msg.metadata()["rpc-status"]["code"], msg.metadata()["rpc-status"]["why"])


config = CameraConfig()
config.sampling.frequency.value = 10.0
config.image.resolution.width = 640
config.image.resolution.height = 480
config.image.color_space.value = ColorSpaces.Value("GRAY")
config.camera.exposure.ratio = 0.1
config.camera.exposure.automatic = False 
config.camera.gain.ratio = 0.05
config.camera.gain.automatic = False 

msg = Message()
msg.pack(config)
msg.set_reply_to(subscription)
msg.set_on_reply(on_set_config)
msg.set_topic("CameraGateway.10.SetConfig")
channel.publish(msg)


def on_get_config(msg, ctx):
    print(msg.metadata()["rpc-status"]["code"], msg.metadata()["rpc-status"]["why"],
          msg.unpack(CameraConfig))
    sys.exit(0)


selector = FieldSelector(fields=[CameraConfigFields.Value("ALL")])
msg2 = Message()
msg2.pack(selector)
msg2.set_reply_to(subscription)
msg2.set_on_reply(on_get_config)
msg2.set_topic("CameraGateway.10.GetConfig")
channel.publish(msg2)

channel.listen()
