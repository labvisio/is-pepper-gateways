from is_wire.core import Logger
from gateway import RobotGateway
from driver import PepperRobotDriver
import os

log = Logger("Service")


def env_or_default(env, default):
    value = os.environ[env] if env in os.environ else default
    log.info("{}='{}'".format(env, value))
    return value


broker_uri = env_or_default("BROKER_URI", "amqp://10.10.2.20:30000")
robot_uri = env_or_default("ROBOT_URI", "10.10.0.111:9559")
#robot_uri = env_or_default("ROBOT_URI", "localhost:33165")
#robot_uri = env_or_default("ROBOT_URI", "10.10.0.111:9559")
base_frame_id = int(env_or_default("BASE_FRAME_ID", "2000"))
world_frame_id = int(env_or_default("WORLD_FRAME_ID", "2001"))
robot_id = int(env_or_default("ROBOT_ID", "0"))

driver = PepperRobotDriver(
    robot_uri=robot_uri,
    base_frame_id=base_frame_id,
    world_frame_id=world_frame_id)

service = RobotGateway(driver=driver)
service.run(id=robot_id, broker_uri=broker_uri)
