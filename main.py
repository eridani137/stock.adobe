import asyncio
import logging
import os.path
from datetime import datetime

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
        count = input("Введите количество страниц: ")
        try:
            numer = int(count)
            return numer
        except ValueError:
            print("Некорректное число. Попробуйте ещё раз.")


async def main():
    url = get_url()
    count = get_count()
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    file_path = os.path.join(os.path.curdir, "results", timestamp + '.txt')
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    passed_pages = 0
    with open(file_path, 'a', encoding='utf-8') as file:
        async with AsyncCamoufox(
                **config.BROWSER_OPTIONS
        ) as browser:

            main_page = browser.pages[0]
            await main_page.goto(url, wait_until="networkidle")

            while passed_pages < count:
                await asyncio.sleep(5)
                await main_page.wait_for_load_state("networkidle")
                images = await main_page.query_selector_all(
                    "xpath=//div[@id='search-results']/div//meta[@itemprop='name']")
                if images:
                    for image in images:
                        parent = await image.evaluate_handle("el => el.parentElement")
                        await parent.evaluate("el => el.scrollIntoView({behavior: 'smooth', block: 'center'})")
                        image_name = await image.get_attribute("content")
                        image_name_stripped = image_name.strip()
                        file.write("{}\n".format(image_name_stripped))
                        logger.info(image_name_stripped)
                passed_pages = passed_pages + 1
                next_page = await main_page.query_selector(
                    "xpath=//div[@id='pagination-element']/nav//i[@class='mti-icon icon-arrow-right mti-large']/../..")
                if next_page:
                    await next_page.scroll_into_view_if_needed()
                    await next_page.click()
                else:
                    logger.warning("Кнопка следующей страницы не найдена")
                    break

            logger.warning(f"Прошли {count} страниц(ы), завершаем работу")
            await browser.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Процесс прерван пользователем.")
    except Exception as e:
        logger.critical(f"Произошла непредвиденная ошибка: {e}", exc_info=True)
