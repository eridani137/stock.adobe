import asyncio
import logging
import os.path
import re
from datetime import datetime
import csv

from camoufox import AsyncCamoufox

import config
from config import is_valid_url
from configure_logger import configure

logger = logging.getLogger(__name__)
configure(logger)


def get_url() -> str:
    while True:
        url = input("Введите ссылку: ")
        if is_valid_url(url):
            return url
        print("Некорректная ссылка. Попробуйте ещё раз.")


def get_count() -> int:
    while True:
        count = input("Введите количество страниц(0 - без ограничений): ")
        try:
            numer = int(count)
            return numer
        except ValueError:
            print("Некорректное число. Попробуйте ещё раз.")


async def main():
    url = get_url()
    count = get_count()

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    file_path = os.path.join(os.path.curdir, "results", timestamp + '.csv')
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    passed_pages = 0
    index = 1
    browser = None

    try:
        with open(file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['ID', 'Prompt'])

            async with AsyncCamoufox(
                    **config.BROWSER_OPTIONS
            ) as browser_instance:
                browser = browser_instance
                main_page = browser.pages[0]
                await main_page.goto(url, wait_until="networkidle")

                while True:
                    images = await main_page.query_selector_all(
                        "xpath=//div[@id='search-results']/div//meta[@itemprop='name']")

                    if images:
                        for image in images:
                            image_name = await image.get_attribute("content")

                            if image_name:
                                image_name_stripped = image_name.replace('\n', ' ').strip()
                                image_name_stripped = re.sub(r'\s+', ' ', image_name_stripped).strip()

                                writer.writerow([index, image_name_stripped])
                                logger.info(f"[{index}] {image_name_stripped}")
                                index += 1
                            else:
                                logger.warning("Обнаружен элемент изображения без атрибута 'content'. Пропускаем")
                    else:
                        logger.warning("На текущей странице не найдено изображений")

                    passed_pages += 1

                    if 0 < count <= passed_pages:
                        logger.warning(f"Достигли заданное количество страниц")
                        break

                    max_retries = 3
                    next_page_clicked = False

                    for retry in range(max_retries):
                        try:
                            await main_page.wait_for_timeout(1000)

                            next_page = await main_page.query_selector(
                                "xpath=//div[@id='pagination-element']/nav/span[last()]/button")

                            if next_page:
                                is_attached = await next_page.evaluate("el => el.isConnected")
                                if not is_attached:
                                    logger.warning(f"Элемент кнопки не прикреплен к DOM, повторная попытка {retry + 1}")
                                    continue

                                next_page_locator = main_page.locator(
                                    "xpath=//div[@id='pagination-element']/nav/span[last()]/button")

                                await next_page_locator.scroll_into_view_if_needed()
                                await next_page_locator.click()

                                await main_page.wait_for_load_state("networkidle")

                                next_page_clicked = True
                                break
                            else:
                                logger.warning("Кнопка следующей страницы не найдена")
                                break

                        except Exception as e:
                            logger.warning(
                                f"Ошибка при попытке перейти на следующую страницу (попытка {retry + 1}): {e}")
                            if retry < max_retries - 1:
                                await main_page.wait_for_timeout(2000)
                                continue
                            else:
                                logger.error("Не удалось перейти на следующую страницу после всех попыток")
                                break

                    if not next_page_clicked:
                        logger.warning("Не удалось найти или нажать кнопку следующей страницы")
                        break

                    await main_page.wait_for_timeout(5000)

                logger.warning(f"Пройдено {count} страниц(ы), завершаем работу")
                await browser.close()

    except Exception as e:
        logger.error(f"Произошла ошибка: {e}", exc_info=True)
    finally:
        if browser:
            await browser.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Процесс прерван пользователем.")
    except Exception as e:
        logger.critical(f"Произошла непредвиденная ошибка: {e}", exc_info=True)
