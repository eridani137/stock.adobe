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
        count = input("Введите количество страниц (0 - без ограничения): ")
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
    index = 0
    with open(file_path, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['ID', 'Prompt'])

        async with AsyncCamoufox(
                **config.BROWSER_OPTIONS
        ) as browser:

            main_page = browser.pages[0]
            await main_page.goto(url, wait_until="networkidle")

            while True:
                if 0 < count <= passed_pages:
                    logger.warning(f"Достигли заданное количество страниц")
                    break

                images = await main_page.query_selector_all(
                    "xpath=//div[@id='search-results']/div//meta[@itemprop='name']")
                if images:
                    for image in images:
                        parent = await image.evaluate_handle("el => el.parentElement")
                        await parent.evaluate("el => el.scrollIntoView({behavior: 'smooth', block: 'center'})")

                        image_name = await image.get_attribute("content")
                        image_name_stripped = image_name.replace('\n', ' ').strip()
                        image_name_stripped = re.sub(r'\s+', ' ', image_name_stripped).strip()

                        writer.writerow([index, image_name_stripped])
                        logger.info(f"[{index}] {image_name_stripped}")
                        index += 1

                passed_pages += 1
                next_page = await main_page.query_selector(
                    "xpath=//div[@id='pagination-element']/nav//i[@class='mti-icon icon-arrow-right mti-large']/../..")
                if next_page:
                    await next_page.scroll_into_view_if_needed()
                    await next_page.click()
                    await asyncio.sleep(5)
                    await main_page.wait_for_load_state("networkidle")
                else:
                    logger.warning("Кнопка следующей страницы не найдена")
                    break

            logger.warning(f"Пройдено {count} страниц(ы), завершаем работу")
            await browser.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Процесс прерван пользователем.")
    except Exception as e:
        logger.critical(f"Произошла непредвиденная ошибка: {e}", exc_info=True)
