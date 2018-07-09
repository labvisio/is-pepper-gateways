from gateway import CameraGateway
from driver import PepperCameraDriver, kPepperTopCamera

#driver = PepperCameraDriver(robot_uri="localhost:45093", camera_id=kPepperTopCamera)
#service = CameraGateway(driver=driver)
#service.run(id=10, broker_uri="amqp://localhost")

driver = PepperCameraDriver(robot_uri="Ada.local", camera_id=kPepperTopCamera)
service = CameraGateway(driver=driver)
service.run(id=10, broker_uri="amqp://10.10.2.20:30000")