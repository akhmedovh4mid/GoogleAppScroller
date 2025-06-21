import time

from uiautomator2 import Device
from typing import Optional


class GoogleParser:
    PACKAGE_NAME = "com.google.android.googlequicksearchbox"
    DISCOVER_BUTTON_ID = "com.google.android.googlequicksearchbox:id/googleapp_navigation_bar_discover"
    VOICE_SEARCH_DESC = "Voice search"
    VOICE_SEARCH_DESC_RU = "Голосовой поиск"
    MORE_STORIES_DESC = "More stories"
    MORE_STORIES_DESC_RU = "Другие статьи"

    def __init__(
        self,
        device: Device,
        duration: float = 0.5,
    ) -> None:
        """Парсер новостей Google.

        Args:
            device: Экземпляр устройства uiautomator2
            duration: Длительность свайпа в секундах
        """
        self.device = device
        self.duration = duration

        self.top_y: Optional[int] = None
        self.bottom_y: Optional[int] = None

    def swipe(self, duration: float, shift_top: int = 25, shift_bottom: int = 25) -> None:
        """Выполняет свайп.

        Args:
            duration: Длительность свайпа
            shift_top: Отступ от верхней границы
            shift_bottom: Отступ от нижней границы
        """
        center_x = round(self.device.info["displayWidth"] / 2)
        start_point = (center_x, self.bottom_y - shift_bottom)
        end_point = (center_x, self.top_y + shift_top)

        self.device.swipe_points(
            points=[start_point, end_point],
            duration=duration
        )

    def parse_news(self):
        """Парсинг новостной ленты Google."""
        home_button = self.device(resourceId=self.DISCOVER_BUTTON_ID)
        home_button.click()

        top_obj = self.device(description=self.VOICE_SEARCH_DESC)
        if not top_obj.exists():
            top_obj = self.device(description=self.VOICE_SEARCH_DESC_RU)
        self.top_y = top_obj.bounds()[3]

        self.bottom_y = home_button.bounds()[1]

        site_end = self.device(description=self.MORE_STORIES_DESC)
        site_end_ru = self.device(description=self.MORE_STORIES_DESC_RU)
        while True:
            self.swipe(duration=self.duration, shift_bottom=100)

            if site_end.exists() or site_end_ru.exists():
                time.sleep(3)
                home_button.click()
                time.sleep(3)


    def run(self):
        """Запуск парсера."""
        self.device.app_start(package_name=self.PACKAGE_NAME)
        self.device.orientation = "natural"

        try:
            self.parse_news()

        except Exception as e:
            print(e)

        finally:
            self.device.app_stop(package_name=self.PACKAGE_NAME)
