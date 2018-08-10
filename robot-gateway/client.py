from is_wire.core import Channel, Subscription, Message
from is_msgs.robot_pb2 import RobotConfig
import os
from sys import argv

uri = os.environ[
    "BROKER_URI"] if "BROKER_URI" in os.environ else "amqp://10.10.2.20:30000"

channel = Channel(uri)
subscription = Subscription(channel)

config = RobotConfig()
config.speed.linear = float(argv[1] or 0.0)
config.speed.angular = float(argv[2] if len(argv) is 3 else 0.0)

channel.publish(
    message=Message(content=config, reply_to=subscription),
    topic="RobotGateway.0.SetConfig")

reply = channel.consume(timeout=1.0)
print reply.status

channel.publish(
    message=Message(reply_to=subscription), topic="RobotGateway.0.GetConfig")

reply = channel.consume(timeout=1.0)
print reply.unpack(RobotConfig)