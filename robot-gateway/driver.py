import time
from threading import RLock
from itertools import izip

import qi
import numpy as np
import threading

from is_msgs.camera_pb2 import FrameTransformation
from is_msgs.common_pb2 import DataType, Speed
from is_wire.core import Logger


def laser_topics():
    topics = []
    for laser in ["Right", "Front", "Left"]:
        for i in xrange(1, 16):
            topics.append(
                "Device/SubDeviceList/Platform/LaserSensor/{}/Horizontal/"
                "Seg{:02d}/X/Sensor/Value".format(laser, i))
            topics.append(
                "Device/SubDeviceList/Platform/LaserSensor/{}/Horizontal/"
                "Seg{:02d}/Y/Sensor/Value".format(laser, i))
    return topics


def grouped_iterator(iterable, n=2):
    return izip(*[iter(iterable)] * n)


def assert_type(instance, _type, name):
    if not isinstance(instance, _type):
        raise TypeError("Object {} must be of type {}".format(
            name, _type.DESCRIPTOR.full_name))


def check_status(ok, why="Operation Failed"):
    if not ok:
        raise RuntimeError(why)


kInteractiveBehavior = "interactive"
kSolitaryBehavior = "solitary"


class PepperRobotDriver(object):
    lock = RLock()
    logger = Logger("PepperRobotDriver")

    def __init__(self,
                 robot_uri,
                 base_frame_id,
                 world_frame_id,
                 behavior=kSolitaryBehavior):
        """
        Args:
            world_frame_id (int): id of the robot world frame of reference,
            this is usually determined by the place where the robot is powered.
        """
        self.qi_app = qi.Application(
            ["is::PepperRobotDriver", "--qi-url=" + robot_uri])
        self.qi_app.start()
        self.qi_session = self.qi_app.session

        self.memory = self.qi_session.service("ALMemory")
        self.motion = self.qi_session.service("ALMotion")
        self.posture = self.qi_session.service("ALRobotPosture")
        self.navigation = self.qi_session.service("ALNavigation")

        self.laser_topics = laser_topics()

        self.base_frame_id = base_frame_id
        self.world_frame_id = world_frame_id

        self.max_linear_speed = 0.35
        self.max_angular_speed = 1.0

        self.deadline = time.time()
        self.sampling_rate = 10.0

        self.posture.goToPosture("StandInit", 0.5)
        self.motion.moveInit()

        # self.proxies["ALAutonomousLife"].setState(behavior)

    def navigate_to(self, x, y):
        thread = threading.Thread(
            target=self.navigation.navigateTo, args=(x, y))
        thread.start()

    def set_speed(self, speed):
        assert_type(speed, Speed, "speed")

        with self.lock:
            linear = max(min(1.0, speed.linear / self.max_linear_speed), -1.0)
            angular = max(
                min(1.0, speed.angular / self.max_angular_speed), -1.0)
            if abs(linear) > 1e-3 or abs(angular) > 1e-3:
                config = [["MaxVelXY", self.max_linear_speed],
                          ["MaxVelTheta", self.max_angular_speed]]
                self.motion.moveToward(linear, 0.0, angular, config)
            else:
                check_status(self.motion.stopMove(), "Failed to stop robot")

    def get_speed(self):
        with self.lock:
            values = self.motion.getRobotVelocity()
        return Speed(linear=values[0], angular=values[2])

    def get_base_pose(self):
        with self.lock:
            diff = self.deadline - time.time()

        if diff > 0:
            time.sleep(diff)

        with self.lock:
            if diff < 0:
                self.deadline = time.time()

            use_sensors = True
            x, y, th = self.motion.getRobotPosition(use_sensors)

            tf = FrameTransformation()
            setattr(tf, "from", self.base_frame_id)
            setattr(tf, "to", self.world_frame_id)

            rows = tf.tf.shape.dims.add()
            rows.size = 4
            rows.name = "rows"
            cols = tf.tf.shape.dims.add()
            cols.size = 4
            cols.name = "cols"
            tf.tf.type = DataType.Value("DOUBLE_TYPE")

            Rz = np.matrix([[np.cos(th), -np.sin(th), 0, 0], \
                            [np.sin(th),  np.cos(th), 0, 0], \
                            [         0,           0, 1, 0], \
                            [         0,           0, 0, 1]])

            T = np.matrix([[1, 0, 0, x], \
                           [0, 1, 0, y], \
                           [0, 0, 1, 0], \
                           [0, 0, 0, 1]])
            T_base_to_world = T * Rz
            tf.tf.doubles.extend(T_base_to_world.reshape(1, -1).tolist()[0])

            self.deadline += 1.0 / self.sampling_rate

        return tf

    def get_laser_scan(self):
        with self.lock:
            values = self.memory.getListData(self.laser_topics)

        # Aggregate all scans from the three lasers as thought they
        # were a single one in the robot base frame
        scan = []

        # Right laser
        for y, x in grouped_iterator(reversed(values[0:30])):
            scan.append(
                np.linalg.norm([
                    x * np.cos(-1.757) - y * np.sin(-1.757) - 0.018,
                    x * np.sin(-1.757) + y * np.cos(-1.757) - 0.090
                ]))

        # Blind zone
        scan.extend([None] * 8)

        # Front laser
        for y, x in grouped_iterator(reversed(values[30:60])):
            scan.append(np.linalg.norm([x + 0.056, y]))

        # Blind zone
        scan.extend([None] * 8)

        # Left laser
        for y, x in grouped_iterator(reversed(values[60:90])):
            scan.append(
                np.linalg.norm([
                    x * np.cos(-1.757) - y * np.sin(-1.757) - 0.018,
                    x * np.sin(-1.757) + y * np.cos(-1.757) + 0.090
                ]))

        return scan
