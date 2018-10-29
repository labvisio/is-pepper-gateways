from is_wire.core import Logger
from gateway import CameraGateway
from driver import PepperCameraDriver, kPepperTopCamera, \
                   kPepperBottomCamera, kPepperDepthCamera
import os

log = Logger("Service")


def env_or_default(env, default):
    value = os.environ[env] if env in os.environ else default
    log.info("{}='{}'".format(env, value))
    return value


cameras = {
    "top": kPepperTopCamera,
    "bottom": kPepperBottomCamera,
    "depth": kPepperDepthCamera,
}

broker_uri = env_or_default("BROKER_URI", "amqp://10.10.2.20:30000")
robot_uri = env_or_default("ROBOT_URI", "localhost:9559")
robot_camera = env_or_default("ROBOT_CAMERA", "TOP").lower()
base_frame_id = int(env_or_default("BASE_FRAME_ID", "2000"))
camera_frame_id = int(env_or_default("CAMERA_FRAME_ID", "10"))

driver = PepperCameraDriver(
    robot_uri=robot_uri,
    camera_id=cameras[robot_camera],
    camera_frame_id=camera_frame_id,
    base_frame_id=base_frame_id)

service = CameraGateway(driver=driver)
service.run(id=camera_frame_id, broker_uri=broker_uri)
