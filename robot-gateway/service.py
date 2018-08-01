from gateway import RobotGateway
from driver import PepperRobotDriver
import os

broker_uri = os.environ[
    "BROKER_URI"] if "BROKER_URI" in os.environ else "amqp://10.10.2.20:30000"
robot_uri = os.environ[
    "ROBOT_URI"] if "ROBOT_URI" in os.environ else "localhost:9559"

driver = PepperRobotDriver(
    robot_uri=robot_uri, base_frame_id=2000, world_frame_id=2001)

service = RobotGateway(driver=driver)
service.run(id=0, broker_uri=broker_uri)
