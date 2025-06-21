import uiautomator2

from typing import List
from uiautomator2 import Device


def get_android_devices_list() -> List[Device]:
    """Возвращает список подключенных Android-устройств.

    Returns:
        List[Device]: Список объектов Device.
    """

    devices = uiautomator2.adbutils.adb.list()
    return [Device(serial=device_info.serial) for device_info in devices]
