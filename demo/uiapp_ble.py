import sys
import os
import numpy
from enum import Enum, auto
import signal
import asyncio
from bleak import BleakScanner, BleakClient
from threading import Thread
from PIL import Image
import matplotlib.pyplot as plt
from datetime import datetime
from matplotlib import animation


# =========================
# Gesture definitions
# =========================

class Gestures(Enum):
    IDLE = 1
    UNKNOWN = 2
    SWIPE_RIGHT = 3
    SWIPE_LEFT = 4
    DOUBLE_SHAKE = 5
    DOUBLE_THUMB = 6
    ROTATION_RIGHT = 7
    ROTATION_LEFT = 8


gestures_string_names = {
    Gestures.UNKNOWN: "UNKNOWN GESTURE",
    Gestures.SWIPE_RIGHT: "SWIPE RIGHT",
    Gestures.SWIPE_LEFT: "SWIPE LEFT",
    Gestures.DOUBLE_SHAKE: "DOUBLE SHAKE",
    Gestures.DOUBLE_THUMB: "DOUBLE THUMB",
    Gestures.ROTATION_RIGHT: "ROTATION RIGHT",
    Gestures.ROTATION_LEFT: "ROTATION LEFT",
    Gestures.IDLE: "NO MOVEMENTS",
}


# =========================
# BLE STATE MACHINE
# =========================

class BLEState(Enum):
    SCANNING = auto()
    CONNECTING = auto()
    LISTENING = auto()


class BLEManager:
    def __init__(self, device_name, characteristic_uuid):
        self.device_name = device_name
        self.char_uuid = characteristic_uuid

        self.state = BLEState.SCANNING
        self.device = None
        self.client = None

        self.disconnect_event = asyncio.Event()

    # Must be sync according to bleak docs
    def on_disconnect(self, client):
        print("BLE → Device disconnected, restarting scan")
        self.disconnect_event.set()

    async def scan(self):
        print("BLE → Scanning...")
        devices = await BleakScanner.discover()

        for device in devices:
            if device.name and (
                device.name == self.device_name
                or device.name in self.device_name
            ):
                print(f"BLE → Found {device.name}")
                self.device = device
                self.state = BLEState.CONNECTING
                return

        await asyncio.sleep(2)

    async def connect(self):
        print(f"BLE → Connecting to {self.device.name}")
        self.disconnect_event.clear()

        self.client = BleakClient(
            self.device,
            disconnected_callback=self.on_disconnect
        )

        try:
            await self.client.connect()
            print("BLE → Connected")
            await asyncio.sleep(1) 
            self.state = BLEState.LISTENING
        except Exception as e:
            print(f"BLE → Connection failed: {e}")
            self.state = BLEState.SCANNING

    async def listen(self):
        characteristic = None

        for service in self.client.services:
            for char in service.characteristics:
                if char.uuid == self.char_uuid:
                    characteristic = char
                    break

        if not characteristic:
            print("BLE → Characteristic not found")
            self.state = BLEState.SCANNING
            return

        def notification_handler(sender, data):
            ble_str = data.decode("utf-8").strip()
            print(ble_str)

            predicted_class_str = ble_str.split(",")[0]
            probability_str = ble_str.split(",")[1].strip()

            class_label_raw = int(predicted_class_str) + 1
            prob_percentage = int(probability_str)

            class_label = Gestures(class_label_raw)
            class_name = gestures_string_names[class_label]

            state.update_image = not (
                state.current_activity == class_label
                and class_label == Gestures.UNKNOWN
            )
            state.current_activity = class_label

            print("{0}, probability {1} %".format(class_name, prob_percentage))
            process_device_output_message(
                f"{class_name}, {prob_percentage}%"
            )

        await self.client.start_notify(
            characteristic.uuid, notification_handler
        )

        print("BLE → Listening")

        # Block until disconnect
        await self.disconnect_event.wait()
        await self.client.disconnect()

        print("BLE → Stopping notifications")
        try:
            await self.client.stop_notify(characteristic.uuid)
        except Exception:
            pass

        self.state = BLEState.SCANNING

    async def run(self):
        while True:
            if self.state == BLEState.SCANNING:
                await self.scan()
            elif self.state == BLEState.CONNECTING:
                await self.connect()
            elif self.state == BLEState.LISTENING:
                await self.listen()


def thread_ble():
    manager = BLEManager(
        "Neuton NRF RemoteControl",
        "516a51c4-b1e1-47fa-8327-8acaeb3399eb"
    )
    asyncio.run(manager.run())


# =========================
# UI STATE (UNCHANGED)
# =========================

class State:
    def __init__(self, current_activity=Gestures.UNKNOWN, update_image=True):
        self.current_activity = current_activity
        self.update_image = update_image


state = State()
model_inferences_str_buffer = []


# =========================
# IMAGE / UI HELPERS
# =========================

def resize_icon_image(image, resize_percent=25):
    w, h = image.size
    return image.resize(
        (int(w * resize_percent / 100), int(h * resize_percent / 100))
    )


def prepare_image(current_activity=Gestures.UNKNOWN, update_image=False):
    result_image = main_img.copy()
    if update_image:
        images = {
            Gestures.UNKNOWN: activity_unknown_img,
            Gestures.SWIPE_RIGHT: activity_swipe_right_img,
            Gestures.SWIPE_LEFT: activity_swipe_left_img,
            Gestures.DOUBLE_SHAKE: activity_double_shake_img,
            Gestures.DOUBLE_THUMB: activity_double_thumb_img,
            Gestures.ROTATION_RIGHT: activity_rotation_right_img,
            Gestures.ROTATION_LEFT: activity_rotation_left_img,
            Gestures.IDLE: activity_idle_img,
        }

        img = images[current_activity]
        x = 320 - img.size[0] // 2
        y = 250 - img.size[1] // 2

        if img.mode == "RGBA":
            result_image.paste(img, (x, y), img)
        else:
            result_image.paste(img, (x, y))

    return result_image


def get_image(activity, update):
    return prepare_image(activity, update)


def update_realtime_inference_labels(text):
    timestamp = datetime.now().strftime("%M:%S:%f")[:-3]
    if len(model_inferences_str_buffer) == 3:
        model_inferences_str_buffer.pop(0)
    model_inferences_str_buffer.append((text, timestamp))


def process_device_output_message(read_str):
    update_realtime_inference_labels(read_str)


def animate(_):
    img = get_image(state.current_activity, state.update_image)
    ax.clear()
    ax.imshow(numpy.array(img))
    ax.axis("off")

    label = gestures_string_names[state.current_activity]
    ax.text(320, 420, label, ha="center", color="white", size=16)

    y = 508 + 22 * 3
    for line, ts in reversed(model_inferences_str_buffer):
        ax.text(60, y, f"({ts}) {line}", color="yellow", size=12)
        y -= 22


# =========================
# SHUTDOWN
# =========================

def signal_handler(sig, frame):
    plt.close('all')  # Close all matplotlib windows
    os._exit(0) 

signal.signal(signal.SIGINT, signal_handler)


# =========================
# MAIN
# =========================

dir_path = os.path.dirname(os.path.abspath(__file__))
material_path = os.path.join(dir_path, "assets")

main_img = Image.open(os.path.join(material_path, "Background.png"))

activity_idle_img = resize_icon_image(Image.open(os.path.join(material_path, "Idle.png")))
activity_unknown_img = resize_icon_image(Image.open(os.path.join(material_path, "Unknown.png")))
activity_swipe_right_img = resize_icon_image(Image.open(os.path.join(material_path, "SwipeRight.png")))
activity_swipe_left_img = resize_icon_image(Image.open(os.path.join(material_path, "SwipeLeft.png")))
activity_double_shake_img = resize_icon_image(Image.open(os.path.join(material_path, "DoubleShake.png")))
activity_double_thumb_img = resize_icon_image(Image.open(os.path.join(material_path, "DoubleThumb.png")))
activity_rotation_right_img = resize_icon_image(Image.open(os.path.join(material_path, "RotationRight.png")))
activity_rotation_left_img = resize_icon_image(Image.open(os.path.join(material_path, "RotationLeft.png")))

fig, ax = plt.subplots(1, figsize=(15, 10))
ani = animation.FuncAnimation(fig, animate, interval=50, cache_frame_data=False)

Thread(target=thread_ble, daemon=True).start()

plt.show()
