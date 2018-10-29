from is_wire.core import Channel, Subscription, Message, Logger
from is_msgs.common_pb2 import Position
import os
from sys import argv, exit

log = Logger(name="client")

uri = os.environ[
    "BROKER_URI"] if "BROKER_URI" in os.environ else "amqp://10.10.2.20:30000"
log.info("uri={}", uri)
if len(argv) != 3:
    log.error("Usage: python navigate.py <X> <Y>")
    exit(-1)

channel = Channel(uri)
subscription = Subscription(channel)

position = Position()
position.x = float(argv[1])
position.y = float(argv[2])

channel.publish(
    message=Message(content=position, reply_to=subscription),
    topic="RobotGateway.0.NavigateTo")

reply = channel.consume(timeout=1.0)
log.info("status={}", reply.status)