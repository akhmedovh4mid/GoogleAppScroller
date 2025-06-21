import time
import pytesseract

from uiautomator2 import Device
from PIL import ImageEnhance, Image
from typing import Literal, Dict, Optional


class YoutubeParser:
    HOME_BUTTON = {"description": "Home", "className": "android.widget.Button"}
    REC_TOP_OBJECT = "com.android.systemui:id/battery"
    REC_BOTTOM_OBJECT = "com.google.android.youtube:id/bottom_bar_container"
    PLAY_BUTTON = "com.google.android.youtube:id/watch_player"
    LINK_TOP_OBJECT = "com.android.systemui:id/battery"
    LINK_BOTTOM_OBJECT = "com.google.android.youtube:id/action_bar_root"
    APP_NAME = "com.google.android.youtube"

    def __init__(
        self,
        device: Device,
        parsing: Literal["links", "recommendations"],
        duration: float = 0.5,
    ) -> None:
        """Парсер YouTube для автоматизации взаимодействия с приложением через UI Automator.

        Args:
            device: Экземпляр подключенного устройства
            parsing: Режим работы парсера ('links' или 'recommendations')
            duration: Длительность анимации свайпа (по умолчанию 0.5 сек)
        """
        self.device = device
        self.parsing = parsing
        self.duration = duration

        self.top_y: int = None
        self.bottom_y: int = None

    @staticmethod
    def get_screen_data(image: Image, lang: str, scale: bool = False) -> Dict:
        """Обрабатывает скриншот для извлечения текста через OCR.

        Args:
            image: Скриншот для обработки
            lang: Язык для распознавания (по умолчанию 'eng')
            scale: Масштабировать ли изображение (улучшает точность для мелкого текста)

        Returns:
            Словарь с распознанным текстом и метаданными в формате pytesseract
        """
        if scale:
            image = image.resize(size=(image.width * 4, image.height * 4))

        image = ImageEnhance.Contrast(image).enhance(1.5)
        data: dict = pytesseract.image_to_data(
            image=image,
            lang=lang,
            output_type=pytesseract.Output.DICT
        )
        return data

    def wait_load_video(self) -> Optional[Literal["comments", "concept", "sponsored"]]:
        """Ожидает загрузку видео и определяет его тип.

        Returns:
            Тип контента:
            - 'comments' - обычное видео с комментариями
            - 'concept' - видео с ключевыми концептами
            - 'sponsored' - спонсорский контент
            None - если тип не определен
        """
        time.sleep(2)
        count: int = 0
        comment_count: int = 0
        while count < 10:
            time.sleep(0.25)
            screenshot = self.device.screenshot()
            screenshot_data = self.get_screen_data(image=screenshot, lang="eng")
            _union_text_for_check: str = " ".join(screenshot_data["text"])

            if ("comments" in _union_text_for_check.lower()):
                comment_count += 1
            elif ("key concepts" in _union_text_for_check.lower()):
                return "concepts"
            elif "sponsored" in _union_text_for_check.lower():
                return "sponsored"

            if comment_count == 3:
                return "comments"

            count += 1

        return None

    def open_link(self, link: str) -> None:
        """Открывает YouTube-ссылку на устройстве.

        Args:
            link: Полная URL-ссылка на видео
        """
        self.device.shell(f"am start -a android.intent.action.VIEW -d \"{link}\" com.google.android.youtube")

    def swipe(self, duration: float, shift_top: int = 25, shift_bottom: int = 25) -> None:
        """Выполняет свайп по экрану между границами.

        Args:
            duration: Длительность анимации (в секундах)
            shift_top: Отступ от верхней границы (в пикселях)
            shift_bottom: Отступ от нижней границы (в пикселях)
        """
        center_x = round(self.device.info["displayWidth"] / 2)

        self.device.swipe_points(
            points=[
                (center_x, self.bottom_y - shift_bottom),
                (center_x, self.top_y + shift_top)
            ],
            duration=duration
        )

    def parse_recommendations(self) -> None:
        """Парсит рекомендации на главной странице YouTube.

        Алгоритм:
        1. Переходит на главный экран
        2. Определяет границы рабочей области
        3. Выполняет серию свайпов для загрузки рекомендаций
        """
        home_button = self.device(**self.HOME_BUTTON)
        home_button.click()

        top_obj = self.device(resourceId=self.REC_TOP_OBJECT)
        self.top_y = top_obj.bounds()[3]

        bottom_obj = self.device(resourceId=self.REC_BOTTOM_OBJECT)
        self.bottom_y = bottom_obj.bounds()[1]

        count = 0
        while count < 45:
            self.swipe(duration=self.duration)
            count += 1

    def parse_links(self) -> None:
        """Парсит видео из файла с ссылками.

        Для каждого видео:
        1. Открывает ссылку
        2. Определяет тип контента
        3. Выполняет взаимодействия в зависимости от типа
        """
        with open("links.txt") as file:
            links = file.readlines()

        for link in links:
            self.open_link(link=link)

            result = self.wait_load_video()

            if result in ["comments", "concepts"]:
                play_button = self.device(resourceId=self.PLAY_BUTTON)
                play_button.click()
                play_button.click()

            elif result == "sponsored":
                links.append(link)
                continue

            else:
                continue

            top_obj = self.device(resourceId=self.LINK_TOP_OBJECT)
            self.top_y = top_obj.bounds()[3]

            bottom_obj = self.device(resourceId=self.LINK_BOTTOM_OBJECT)
            self.bottom_y = bottom_obj.bounds()[3]

            count = 0
            while count < 16:
                self.swipe(duration=self.duration, shift_bottom=100)
                count += 1


    def run(self) -> None:
        """Основной метод запуска парсера.

        Handles:
        - Запуск/остановку приложения
        - Обработку ошибок
        - Выбор режима работы
        """
        self.device.app_start(package_name=self.APP_NAME)
        self.device.orientation = "natural"

        try:
            if self.parsing == "recommendations":
                self.parse_recommendations()
            else:
                self.parse_links()

        except Exception as e:
            print(e)

        finally:
            self.device.app_stop(package_name=self.APP_NAME)
