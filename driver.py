import qi
import vision_definitions as qivis
import numpy as np
import cv2
import sys
from is_msgs.image_pb2 import *
from is_msgs.camera_pb2 import *
from is_msgs.wire_pb2 import Status, StatusCode
from is_wire.core import Logger
from threading import RLock
import time


def assert_type(instance, _type, name):
    if not isinstance(instance, _type):
        raise TypeError("Object {} must be of type {}".format(name, _type.DESCRIPTOR.full_name))


def check_status(ok, why="Operation Failed"):
    if not ok or ok == -1:
        raise RuntimeError(why)


kPepperTopCamera = qivis.kTopCamera
kPepperBottomCamera = qivis.kBottomCamera
kPepperDepth = qivis.kDepthCamera

parameters = {
    "brightness": {
        "id": qivis.kCameraBrightnessID,
        "max": 255,
        "min": 0,
    },
    "exposure": {
        "id": qivis.kCameraExposureID,
        "max": 65536,
        "min": 0,
        "auto_id": qivis.kCameraAutoExpositionID,
    },
    "hue": {
        "id": qivis.kCameraHueID,
        "max": 180,
        "min": -180,
    },
    "saturation": {
        "id": qivis.kCameraSaturationID,
        "max": 255,
        "min": 0,
    },
    "gain": {
        "id": qivis.kCameraGainID,
        "max": 1024,
        "min": 0,
        "auto_id": qivis.kCameraAutoGainID
    },
    "focus": {
        "auto_id": qivis.kCameraAutoFocusID
    }
}


def resolution_is_to_naoqi(resolution):
    if resolution.width == 80 and resolution.height == 60:
        return qivis.kQQQVGA
    if resolution.width == 160 and resolution.height == 120:
        return qivis.kQQVGA
    if resolution.width == 320 and resolution.height == 240:
        return qivis.kQVGA
    if resolution.width == 640 and resolution.height == 480:
        return qivis.kVGA
    if resolution.width == 1280 and resolution.height == 960:
        return qivis.k4VGA
    raise RuntimeError(
        "Invalid Resolution Value, expected (80,60) or (160,120) or (320,240) or (640,480) or (1280,960)"
    )


def color_space_is_to_naoqi(color_space):
    if color_space == ColorSpaces.Value("RGB") or \
        color_space == ColorSpaces.Value("GRAY"):
        return qivis.kBGRColorSpace
    if color_space == ColorSpaces.Value("HSV"):
        return qivis.kHSVColorSpace
    if color_space == ColorSpaces.Value("YCbCr"):
        return qivis.kYYCbCrColorSpace
    raise RuntimeError("Invalid ColorSpace value")


class PepperCameraDriver(object):
    lock = RLock()
    logger = Logger("PepperCameraDriver")

    def __init__(self, robot_uri, camera_id):
        self.qi_app = qi.Application(["is::PepperCameraDriver", "--qi-url=" + robot_uri])
        self.qi_app.start()
        self.qi_session = self.qi_app.session

        self.local = True if "localhost" in robot_uri or "127.0.0.1" in robot_uri else False

        self.video = self.qi_session.service("ALVideoDevice")

        self.camera = None
        self.camera_id = camera_id

        self.fps = 10.0
        self.deadline = None
        self.resolution = Resolution(width=320, height=240)
        self.color_space = ColorSpaces.Value("GRAY")
        image_format = ImageFormat()
        image_format.format = ImageFormats.Value("JPEG")
        image_format.compression.value = 0.8
        self.set_image_format(image_format)

    def __set_parameter(self, name, camera_setting):
        assert_type(camera_setting, CameraSetting, "camera_setting")
        with self.lock:
            parameter = parameters[name]
            if "auto_id" in parameter:
                check_status(
                    self.video.setCameraParameter(self.camera, parameter["auto_id"],
                                                  camera_setting.automatic))
            if "id" in parameter and not camera_setting.automatic:
                ratio = (parameter["max"] - parameter["min"]) * camera_setting.ratio + parameter["min"]
                check_status(self.video.setCameraParameter(self.camera, parameter["id"], ratio))

    def __get_parameter(self, name):
        camera_setting = CameraSetting()
        with self.lock:
            parameter = parameters[name]
            if "auto_id" in parameter:
                camera_setting.automatic = self.video.getCameraParameter(self.camera, parameter["auto_id"])
            if "id" in parameter: 
                value = self.video.getCameraParameter(self.camera, parameter["id"])
                camera_setting.ratio = (value - parameter["min"]) / float(parameter["max"] - parameter["min"])
        return camera_setting

    ### Sampling Settings
    def set_sampling_rate(self, value):
        assert_type(value, (int, float), "value")
        with self.lock:
            check_status(self.video.setFrameRate(self.camera, int(value)))
            self.fps = value

    def set_delay(self, value):
        pass

    def get_sampling_rate(self):
        with self.lock:
            value = self.video.getFrameRate(self.camera)
            check_status(value, "Failed to retrieve frame rate")
            self.fps = value
            return value

    def get_delay(self):
        return None

    ### Image Settings
    def set_resolution(self, resolution):
        assert_type(resolution, Resolution, "resolution")
        with self.lock:
            check_status(
                self.video.setResolution(self.camera, resolution_is_to_naoqi(resolution)),
                "Failed to change resolution")
            self.resolution = resolution

    def set_image_format(self, image_format):
        assert_type(image_format, ImageFormat, "image_format")
        with self.lock:
            if image_format.format == ImageFormats.Value("JPEG"):
                self.encode_format = ".jpeg"
            elif image_format.format == ImageFormats.Value("PNG"):
                self.encode_format = ".png"
            elif image_format.format == ImageFormats.Value("WebP"):
                self.encode_format = ".webp"

            if image_format.HasField("compression"):
                if self.encode_format == '.jpeg':
                    self.encode_parameters = [
                        cv2.IMWRITE_JPEG_QUALITY,
                        int(image_format.compression.value * (100 - 0) + 0)
                    ]
                elif self.encode_format == '.png':
                    self.encode_parameters = [
                        cv2.IMWRITE_PNG_COMPRESSION,
                        int(image_format.compression.value * (9 - 0) + 0)
                    ]
                elif self.encode_format == '.webp':
                    self.encode_parameters = [
                        cv2.IMWRITE_WEBP_QUALITY,
                        int(image_format.compression.value * (100 - 1) + 1)
                    ]

    def set_color_space(self, color_space):
        assert_type(color_space, int, "color_space")
        with self.lock:
            check_status(
                self.video.setColorSpace(self.camera, color_space_is_to_naoqi(color_space)),
                "Failed to set color space")
            self.color_space = color_space

    def set_region_of_interest(self, bounding_poly):
        pass

    def get_resolution(self):
        with self.lock:
            value = self.video.getResolution(self.camera)
        resolution = Resolution()
        if value == qivis.kQQQVGA:
            resolution.width = 80
            resolution.height = 60
        elif value == qivis.kQQVGA:
            resolution.width = 160
            resolution.height = 120
        elif value == qivis.kQVGA:
            resolution.width = 320
            resolution.height = 240
        elif value == qivis.kVGA:
            resolution.width = 640
            resolution.height = 480
        elif value == qivis.k4VGA:
            resolution.width = 1280
            resolution.height = 960
        elif value == qivis.k16VGA:
            resolution.width = 2560
            resolution.height = 1920
        self.resolution = resolution
        return resolution

    def get_image_format(self):
        image_format = ImageFormat()
        with self.lock:
            if self.encode_format == ".jpeg":
                image_format.format = ImageFormats.Value("JPEG")
                image_format.compression.value = self.encode_parameters[1] / 100.0
            elif self.encode_format == ".png":
                image_format.format = ImageFormats.Value("PNG")
                image_format.compression.value = self.encode_parameters[1] / 9.0
            elif self.encode_format == ".webp":
                image_format.format = ImageFormats.Value("WebP")
                image_format.compression.value = (self.encode_parameters[1] - 1) / 99.0
        return image_format

    def get_color_space(self):
        with self.lock:
            return self.color_space

    def get_region_of_interest(self):
        return None

    ### Camera Settings
    def set_brightness(self, camera_setting):
        self.__set_parameter("brightness", camera_setting)

    def set_exposure(self, camera_setting):
        self.__set_parameter("exposure", camera_setting)

    def set_focus(self, camera_setting):
        self.__set_parameter("focus", camera_setting)

    def set_sharpness(self, camera_setting):
        pass

    def set_hue(self, camera_setting):
        self.__set_parameter("hue", camera_setting)

    def set_saturation(self, camera_setting):
        self.__set_parameter("saturation", camera_setting)

    def set_gamma(self, camera_setting):
        pass

    def set_shutter(self, camera_setting):
        pass

    def set_gain(self, camera_setting):
        self.__set_parameter("gain", camera_setting)

    def set_white_balance_bu(self, camera_setting):
        pass

    def set_white_balance_rv(self, camera_setting):
        pass

    def set_zoom(self, camera_setting):
        pass

    def set_iris(self, camera_setting):
        pass

    def get_brightness(self):
        return self.__get_parameter("brightness")

    def get_exposure(self):
        return self.__get_parameter("exposure")

    def get_focus(self):
        return self.__get_parameter("focus")

    def get_sharpness(self):
        return None

    def get_hue(self):
        return self.__get_parameter("hue")

    def get_saturation(self):
        return self.__get_parameter("saturation")

    def get_gamma(self):
        return None

    def get_shutter(self):
        return None

    def get_gain(self):
        return self.__get_parameter("gain")

    def get_white_balance_bu(self):
        return None

    def get_white_balance_rv(self):
        return None

    def get_zoom(self):
        return None

    def get_iris(self):
        return None

    def start_capture(self):
        with self.lock:
            resolution = resolution_is_to_naoqi(self.resolution)
            color_space = color_space_is_to_naoqi(self.color_space)
            id = "is::xxPepperCameraDriver.{}".format(self.camera_id)
            self.camera = self.video.subscribeCamera(id, self.camera_id, resolution, color_space,
                                                     int(self.fps))
            self.deadline = time.time() + 1.0 / self.fps

    def stop_capture(self):
        with self.lock:
            self.video.unsubscribe(self.camera)

    def grab_image(self):
        with self.lock:
            diff = self.deadline - time.time()
            if diff > 0:
                time.sleep(diff)
            else:
                self.deadline = time.time()

            before_get = time.time()
            frame = self.video.getImageRemote(self.camera)

            proc_begin = time.time()

            width, height, buffer = frame[0], frame[1], frame[6]
            mat = np.frombuffer(buffer, dtype=np.uint8).reshape(height, width, -1)
            if self.color_space == ColorSpaces.Value("GRAY"):
                mat = cv2.cvtColor(mat, cv2.COLOR_BGR2GRAY)
            image = cv2.imencode(ext=self.encode_format, img=mat, params=self.encode_parameters)

            proc_end = time.time()

            self.logger.info("[GrabImage] New Frame (get={:.1f}ms, proc={:.1f}ms, late={:.1f}ms)",
                             (proc_begin - before_get) * 1000, 
                             (proc_end - proc_begin) * 1000,
                             diff * 1000)
            self.deadline += 1.0 / self.fps

        return Image(data=image[1].tobytes())
