from is_wire.core import Channel, Subscription, Message, Logger
from is_wire.rpc import ServiceProvider, LogInterceptor
from is_msgs.camera_pb2 import CameraConfig, CameraConfigFields
from is_msgs.common_pb2 import FieldSelector
from is_msgs.wire_pb2 import Status, StatusCode
from google.protobuf.empty_pb2 import Empty
from google.protobuf.json_format import MessageToJson
import sys
import signal
from threading import Thread, Event
import traceback


def get_obj(callable, obj):
    value = callable()
    if value != None:
        obj.CopyFrom(value)


def get_val(callable, obj, attr):
    value = callable()
    if value != None:
        setattr(obj, attr, value)


class CameraGateway(object):

    def __init__(self, driver):
        self.driver = driver
        self.logger = Logger("CameraGateway")

    def get_config(self, field_selector):
        code, why = "OK", ""
        camera_config = CameraConfig()
        fields = field_selector.fields
        try:
            if CameraConfigFields.Value("ALL") in fields or \
               CameraConfigFields.Value("SAMPLING_SETTINGS") in fields:
                get_val(self.driver.get_sampling_rate, camera_config.sampling.frequency, "value")
                get_val(self.driver.get_delay, camera_config.sampling.delay, "value")

            if CameraConfigFields.Value("ALL") in fields or \
               CameraConfigFields.Value("IMAGE_SETTINGS") in fields:
                get_obj(self.driver.get_resolution, camera_config.image.resolution)
                get_obj(self.driver.get_image_format, camera_config.image.format)
                get_val(self.driver.get_color_space, camera_config.image.color_space, "value")
                get_obj(self.driver.get_region_of_interest, camera_config.image.region)

            if CameraConfigFields.Value("ALL") in fields or \
               CameraConfigFields.Value("CAMERA_SETTINGS") in fields:
                get_obj(self.driver.get_brightness, camera_config.camera.brightness)
                get_obj(self.driver.get_exposure, camera_config.camera.exposure)
                get_obj(self.driver.get_focus, camera_config.camera.focus)
                get_obj(self.driver.get_gain, camera_config.camera.gain)
                get_obj(self.driver.get_gamma, camera_config.camera.gamma)
                get_obj(self.driver.get_hue, camera_config.camera.hue)
                get_obj(self.driver.get_iris, camera_config.camera.iris)
                get_obj(self.driver.get_saturation, camera_config.camera.saturation)
                get_obj(self.driver.get_sharpness, camera_config.camera.sharpness)
                get_obj(self.driver.get_shutter, camera_config.camera.shutter)
                get_obj(self.driver.get_white_balance_bu, camera_config.camera.white_balance_bu)
                get_obj(self.driver.get_white_balance_rv, camera_config.camera.white_balance_rv)
                get_obj(self.driver.get_zoom, camera_config.camera.zoom)
        except:
            code, why = "INTERNAL_ERROR", "{}".format(traceback.format_exc())
        return camera_config, {"code": code, "why": why}

    def set_config(self, camera_config):
        code, why = "OK", ""
        try:
            if camera_config.HasField("sampling"):
                if camera_config.sampling.HasField("frequency"):
                    self.driver.set_sampling_rate(camera_config.sampling.frequency.value)
                if camera_config.sampling.HasField("delay"):
                    self.driver.set_delay(camera_config.sampling.delay.value)

            if camera_config.HasField("image"):
                if camera_config.image.HasField("resolution"):
                    self.driver.set_resolution(camera_config.image.resolution)
                if camera_config.image.HasField("format"):
                    self.driver.set_image_format(camera_config.image.format)
                if camera_config.image.HasField("color_space"):
                    self.driver.set_color_space(camera_config.image.color_space.value)
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
                    self.driver.set_white_balance_bu(camera_config.camera.white_balance_bu)
                if camera_config.camera.HasField("white_balance_rv"):
                    self.driver.set_white_balance_rv(camera_config.camera.white_balance_rv)
                if camera_config.camera.HasField("zoom"):
                    self.driver.set_zoom(camera_config.camera.zoom)
        except:
            code, why = "INTERNAL_ERROR", "{}".format(traceback.format_exc())
        return Empty(), {"code": code, "why": why}

    def run(self, id, broker_uri):
        name = "CameraGateway.{}".format(id)

        def capture_loop(name, broker_uri, driver, stop):
            channel = Channel(broker_uri)
            driver.start_capture()
            logger = Logger("CameraGateway")
            logger.info("Starting to capture")
            while not stop.is_set():
                image = driver.grab_image()
                message = Message()
                message.set_topic(name + ".Frame")
                message.pack(image)
                channel.publish(message)
            driver.stop_capture()

        stop = Event()
        thread = Thread(target=capture_loop, args=(name, broker_uri, self.driver, stop))
        thread.start()

        def signal_handler(sig, frame, thread, stop):
            print("Shutting down")
            stop.set()
            thread.join()
            sys.exit(0)

        signal.signal(signal.SIGINT, lambda sig, frame: signal_handler(sig, frame, thread, stop))

        channel = Channel(broker_uri)
        server = ServiceProvider(channel)
        server.add_interceptor(LogInterceptor())

        server.delegate(name + ".GetConfig", FieldSelector, CameraConfig, self.get_config)
        server.delegate(name + ".SetConfig", CameraConfig, Empty, self.set_config)

        self.logger.info("Listening for requests")
        channel.listen()