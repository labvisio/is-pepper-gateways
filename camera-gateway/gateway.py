from is_wire.core import Channel, Message, Logger
from is_wire.rpc import ServiceProvider, LogInterceptor

from is_msgs.camera_pb2 import CameraConfig, CameraConfigFields
from is_msgs.common_pb2 import FieldSelector
from google.protobuf.empty_pb2 import Empty

import socket


def get_obj(callable, obj):
    value = callable()
    if value is not None:
        obj.CopyFrom(value)


def get_val(callable, obj, attr):
    value = callable()
    if value is not None:
        setattr(obj, attr, value)


class CameraGateway(object):
    def __init__(self, driver):
        self.driver = driver
        self.logger = Logger("CameraGateway")

    def get_config(self, field_selector, ctx):
        fields = field_selector.fields
        camera_config = CameraConfig()

        if CameraConfigFields.Value("ALL") in fields or \
           CameraConfigFields.Value("SAMPLING_SETTINGS") in fields:
            get_val(self.driver.get_sampling_rate,
                    camera_config.sampling.frequency, "value")
            get_val(self.driver.get_delay, camera_config.sampling.delay,
                    "value")

        if CameraConfigFields.Value("ALL") in fields or \
           CameraConfigFields.Value("IMAGE_SETTINGS") in fields:
            get_obj(self.driver.get_resolution, camera_config.image.resolution)
            get_obj(self.driver.get_image_format, camera_config.image.format)
            get_val(self.driver.get_color_space,
                    camera_config.image.color_space, "value")
            get_obj(self.driver.get_region_of_interest,
                    camera_config.image.region)

        if CameraConfigFields.Value("ALL") in fields or \
           CameraConfigFields.Value("CAMERA_SETTINGS") in fields:
            get_obj(self.driver.get_brightness,
                    camera_config.camera.brightness)
            get_obj(self.driver.get_exposure, camera_config.camera.exposure)
            get_obj(self.driver.get_focus, camera_config.camera.focus)
            get_obj(self.driver.get_gain, camera_config.camera.gain)
            get_obj(self.driver.get_gamma, camera_config.camera.gamma)
            get_obj(self.driver.get_hue, camera_config.camera.hue)
            get_obj(self.driver.get_iris, camera_config.camera.iris)
            get_obj(self.driver.get_saturation,
                    camera_config.camera.saturation)
            get_obj(self.driver.get_sharpness, camera_config.camera.sharpness)
            get_obj(self.driver.get_shutter, camera_config.camera.shutter)
            get_obj(self.driver.get_white_balance_bu,
                    camera_config.camera.white_balance_bu)
            get_obj(self.driver.get_white_balance_rv,
                    camera_config.camera.white_balance_rv)
            get_obj(self.driver.get_zoom, camera_config.camera.zoom)

        return camera_config

    def set_config(self, camera_config, ctx):
        if camera_config.HasField("sampling"):
            if camera_config.sampling.HasField("frequency"):
                self.driver.set_sampling_rate(
                    camera_config.sampling.frequency.value)
            if camera_config.sampling.HasField("delay"):
                self.driver.set_delay(camera_config.sampling.delay.value)

        if camera_config.HasField("image"):
            if camera_config.image.HasField("resolution"):
                self.driver.set_resolution(camera_config.image.resolution)
            if camera_config.image.HasField("format"):
                self.driver.set_image_format(camera_config.image.format)
            if camera_config.image.HasField("color_space"):
                self.driver.set_color_space(
                    camera_config.image.color_space.value)
            if camera_config.image.HasField("region"):
                self.driver.set_region_of_interest(camera_config.image.region)

        if camera_config.HasField("camera"):
            if camera_config.camera.HasField("brightness"):
                self.driver.set_brightness(camera_config.camera.brightness)
            if camera_config.camera.HasField("exposure"):
                self.driver.set_exposure(camera_config.camera.exposure)
            if camera_config.camera.HasField("focus"):
                self.driver.set_focus(camera_config.camera.focus)
            if camera_config.camera.HasField("gain"):
                self.driver.set_gain(camera_config.camera.gain)
            if camera_config.camera.HasField("gamma"):
                self.driver.set_gamma(camera_config.camera.gamma)
            if camera_config.camera.HasField("hue"):
                self.driver.set_hue(camera_config.camera.hue)
            if camera_config.camera.HasField("iris"):
                self.driver.set_iris(camera_config.camera.iris)
            if camera_config.camera.HasField("saturation"):
                self.driver.set_saturation(camera_config.camera.saturation)
            if camera_config.camera.HasField("sharpness"):
                self.driver.set_sharpness(camera_config.camera.sharpness)
            if camera_config.camera.HasField("shutter"):
                self.driver.set_shutter(camera_config.camera.shutter)
            if camera_config.camera.HasField("white_balance_bu"):
                self.driver.set_white_balance_bu(
                    camera_config.camera.white_balance_bu)
            if camera_config.camera.HasField("white_balance_rv"):
                self.driver.set_white_balance_rv(
                    camera_config.camera.white_balance_rv)
            if camera_config.camera.HasField("zoom"):
                self.driver.set_zoom(camera_config.camera.zoom)
        return Empty()

    def run(self, id, broker_uri):
        service_name = "CameraGateway.{}".format(id)

        channel = Channel(broker_uri)
        server = ServiceProvider(channel)

        logging = LogInterceptor()
        server.add_interceptor(logging)

        server.delegate(
            topic=service_name + ".GetConfig",
            request_type=FieldSelector,
            reply_type=CameraConfig,
            function=self.get_config)

        server.delegate(
            topic=service_name + ".SetConfig",
            request_type=CameraConfig,
            reply_type=Empty,
            function=self.set_config)

        self.driver.start_capture()
        self.logger.info("Listening for requests")

        while True:
            image = self.driver.grab_image()
            channel.publish(
                Message(content=image), topic=service_name + ".Frame")

            pose = self.driver.get_pose()
            channel.publish(
                Message(content=pose), topic=service_name + ".Pose")

            try:
                message = channel.consume(timeout=0)
                if server.should_serve(message):
                    server.serve(message)
            except socket.timeout:
                pass