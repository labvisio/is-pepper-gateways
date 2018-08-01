from gateway import CameraGateway
from driver import PepperCameraDriver, kPepperTopCamera
import os

broker_uri = os.environ[
    "BROKER_URI"] if "BROKER_URI" in os.environ else "amqp://10.10.2.20:30000"
robot_uri = os.environ[
    "ROBOT_URI"] if "ROBOT_URI" in os.environ else "localhost:9559"

driver = PepperCameraDriver(
    robot_uri=robot_uri,
    camera_id=kPepperTopCamera,
    camera_frame_id=10,
    base_frame_id=2000)

service = CameraGateway(driver=driver)
service.run(id=10, broker_uri=broker_uri)
