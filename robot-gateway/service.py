from is_wire.core import Logger
from gateway import RobotGateway
from driver import PepperRobotDriver
import json
import sys

log = Logger("Service")

config_path = "conf.json" if len(sys.argv) != 2 else sys.argv[1]
with open(config_path) as f:
    config = json.load(f)

log.info("config_file @'{}':\n{}", config_path, json.dumps(config, indent=4))

driver = PepperRobotDriver(
    robot_uri=config["robot_uri"], parameters=config["driver_params"])

service = RobotGateway(driver=driver)
service.run(id=config["robot_id"], broker_uri=config["broker_uri"])
