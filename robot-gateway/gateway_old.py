from is_wire.core import Channel, Message, Logger, Status, StatusCode
from is_wire.rpc import ServiceProvider, LogInterceptor

from google.protobuf.empty_pb2 import Empty
from is_msgs.common_pb2 import FieldSelector, Position
from is_msgs.robot_pb2 import RobotConfig
from is_msgs.camera_pb2 import FrameTransformations

import socket


def get_obj(callable, obj):
    value = callable()
    if value is not None:
        obj.CopyFrom(value)


def get_val(callable, obj, attr):
    value = callable()
    if value is not None:
        setattr(obj, attr, value)


class RobotGateway(object):
    def __init__(self, driver):
        self.driver = driver
        self.logger = Logger("RobotGateway")

    def get_config(self, field_selector, ctx):
        robot_config = RobotConfig()
        get_obj(self.driver.get_speed, robot_config.speed)
        return robot_config

    def set_config(self, robot_config, ctx):
        if robot_config.HasField("speed"):
            self.driver.set_speed(robot_config.speed)
        return Empty()

    def navigate_to(self, position, ctx):
        self.driver.navigate_to(position.x, position.y)
        return Empty()

    def run(self, id, broker_uri):
        service_name = "RobotGateway.{}".format(id)

        channel = Channel(broker_uri)
        server = ServiceProvider(channel)
        logging = LogInterceptor()
        server.add_interceptor(logging)

        server.delegate(
            topic=service_name + ".GetConfig",
            request_type=FieldSelector,
            reply_type=RobotConfig,
            function=self.get_config)

        server.delegate(
            topic=service_name + ".SetConfig",
            request_type=RobotConfig,
            reply_type=Empty,
            function=self.set_config)

        server.delegate(
            topic=service_name + ".NavigateTo",
            request_type=Position,
            reply_type=Empty,
            function=self.navigate_to)

        self.logger.info("Listening for requests")
        while True:
            pose = self.driver.get_base_pose()
            self.logger.debug("Publishing pose")

            channel.publish(
                #Message(content=pose), topic=service_name + ".Pose")
                Message(content=pose), topic=service_name + ".FrameTransformations")

            try:
                message = channel.consume(timeout=0)
                if server.should_serve(message):
                    server.serve(message)
            except socket.timeout:
                pass
