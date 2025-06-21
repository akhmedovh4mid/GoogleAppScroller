import time
import logging
import argparse
import sys

from pathlib import Path
from uiautomator2 import Device
from multiprocessing import Process, Event

from parsers.common import configure_logging
from parsers.google_parser import GoogleParser
from parsers.youtube_parser import YoutubeParser
from parsers.utils import get_android_devices_list

logger = logging.getLogger(__name__)
configure_logging(level=logging.INFO)


def worker(serial: str, duration: float, parsing: str, stop_event: Event):
    logger.info(f"[{serial}] Запуск worker")

    device = Device(serial)

    try:
        while device.info.get("currentPackageName") == "com.android.systemui":
            if stop_event.is_set():
                logger.info(f"[{serial}] Получен сигнал остановки до старта")
                return
            logger.info(f"[{serial}] Устройство заблокировано. Ожидание разблокировки...")
            time.sleep(0.5)

        if parsing in ("links", "recommendations"):
            parser = YoutubeParser(device=device, duration=duration, parsing=parsing)
        else:
            parser = GoogleParser(device=device, duration=duration)

        logger.info(f"[{serial}] Старт парсинга ({parsing})")

        while not stop_event.is_set():
            parser.run()
            break

    except KeyboardInterrupt:
        # Подавляем Ctrl+C в дочернем процессе
        logger.info(f"[{serial}] Прерывание по Ctrl+C — завершение парсера")

    except Exception as e:
        logger.exception(f"[{serial}] Ошибка в worker: {e}", exc_info=True)

    finally:
        device.app_stop_all()
        logger.info(f"[{serial}] Worker завершил работу")



def parse_args():
    parser = argparse.ArgumentParser(description="Настройка параметров парсинга")

    parser.add_argument(
        "-d", "--duration",
        type=float,
        default=0.5,
        help="Скорость обработки (по умолчанию: 0.5)"
    )

    parser.add_argument(
        "-p", "--parsing",
        type=str,
        choices=["links", "recommendations", "google"],
        default="recommendations",
        help="Тип парсинга: links, recommendations, google"
    )

    return parser.parse_args()


def main():
    """Запускает процессы парсинга на всех доступных Android-устройствах."""
    logger.info("=== Запуск приложения ===")

    args = parse_args()
    devices = get_android_devices_list()
    device_serials = [device.serial for device in devices]

    if not device_serials:
        logger.error("Устройства не найдены. Завершение работы.")
        return

    logger.info(f"Найдено устройств: {device_serials}")

    if args.parsing == "links" and not Path("links.txt").is_file():
        logger.error("Файл links.txt не найден. Завершение работы.")
        return

    processes = []
    stop_event = Event()

    try:
        for serial in device_serials:
            p = Process(
                name=serial,
                target=worker,
                args=(serial, args.duration, args.parsing, stop_event)
            )
            processes.append(p)
            p.start()
            logger.debug(f"Процесс {p.name} запущен")

        logger.info("Ожидание завершения процессов...")
        for p in processes:
            p.join()
            logger.debug(f"Процесс {p.name} завершён")

    except KeyboardInterrupt:
        logger.warning("Получен сигнал прерывания (Ctrl + C). Останавливаем процессы...")
        stop_event.set()

        for p in processes:
            logger.debug(f"Ожидание завершения {p.name} после сигнала остановки...")
            p.join(timeout=5)
            if p.is_alive():
                logger.warning(f"{p.name} не завершился вовремя. Принудительное завершение.")
                p.terminate()
                p.join()

    except Exception as e:
        logger.exception("Ошибка в главном процессе:", exc_info=True)
        stop_event.set()
        for p in processes:
            p.terminate()
            p.join()
        sys.exit(1)

    logger.info("=== Все процессы завершены ===")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Программа прервана пользователем.")
