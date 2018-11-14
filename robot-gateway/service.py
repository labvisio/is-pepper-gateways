from is_wire.core import Logger
from gateway import RobotGateway
from driver import PepperRobotDriver
import json
import sys
import os

log = Logger("Service")

config_path = "conf.json" if len(sys.argv) != 2 else sys.argv[1]
with open(config_path) as f:
    config = json.load(f)

log.info("config_file @'{}':\n{}", config_path, json.dumps(config, indent=4))

def env_or_default(env, default):
    value = os.environ[env] if env in os.environ else default
    log.info("{}='{}'".format(env, value))
    return value

broker_uri = env_or_default("BROKER_URI", config["broker_uri"])
robot_uri = env_or_default("ROBOT_URI", str(config["robot_uri"]))
robot_id = env_or_default("ROBOT_ID", config["robot_id"])


driver = PepperRobotDriver(
    robot_uri=robot_uri, parameters=config["driver_params"])

service = RobotGateway(driver=driver)
service.run(id=robot_id, broker_uri=broker_uri)



