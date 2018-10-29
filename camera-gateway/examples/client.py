from is_wire.core import Channel, Subscription, Message
from is_msgs.camera_pb2 import CameraConfig, CameraConfigFields
from is_msgs.image_pb2 import ColorSpaces
from is_msgs.common_pb2 import FieldSelector
import os

uri = os.environ[
    "BROKER_URI"] if "BROKER_URI" in os.environ else "amqp://10.10.2.20:30000"

channel = Channel(uri)
subscription = Subscription(channel)

config = CameraConfig()
config.sampling.frequency.value = 10.0
config.image.resolution.width = 640
config.image.resolution.height = 480
config.image.color_space.value = ColorSpaces.Value("GRAY")
# config.camera.exposure.ratio = 0.1
# config.camera.gain.ratio = 0.05
# config.camera.gain.automatic = True

channel.publish(
    Message(content=config, reply_to=subscription),
    topic="CameraGateway.10.SetConfig")

reply = channel.consume(timeout=1.0)
print reply

selector = FieldSelector(fields=[CameraConfigFields.Value("ALL")])
channel.publish(
    Message(content=selector, reply_to=subscription),
    topic="CameraGateway.10.GetConfig")

reply = channel.consume(timeout=1.0)
print reply.unpack(CameraConfig)
