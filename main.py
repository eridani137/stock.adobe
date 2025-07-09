import asyncio
import json
import logging
import os.path
import random
import re
import ssl
from datetime import datetime
import csv
from typing import Tuple, List

import nltk
import spacy
import en_core_web_sm
from camoufox import AsyncCamoufox
from nltk import word_tokenize, pos_tag
from nltk.corpus import wordnet
from playwright.async_api import Page

import config
from config import is_valid_url
from configure_logger import configure
import aiohttp
from aiohttp import ClientSession
from parsel import Selector

logger = logging.getLogger(__name__)
configure(logger)

nlp = en_core_web_sm.load()
nltk.download('wordnet')
nltk.download('punkt_tab')
nltk.download('averaged_perceptron_tagger_eng')
nltk.download('omw-1.4')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/135.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'ru,en-US;q=0.7,en;q=0.3',
    'Referer': 'https://stock.adobe.com/',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'Connection': 'keep-alive',
}


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


def create_tls_session(*args, **kwargs) -> ClientSession:
    ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

    try:
        ssl_context.set_ciphers(':'.join([
            "ECDHE-ECDSA-AES128-GCM-SHA256",
            "ECDHE-RSA-AES128-GCM-SHA256",
            "ECDHE-ECDSA-AES256-GCM-SHA384",
            "ECDHE-RSA-AES256-GCM-SHA384",
            "ECDHE-ECDSA-CHACHA20-POLY1305",
            "ECDHE-RSA-CHACHA20-POLY1305",
            "ECDHE-RSA-AES128-SHA",
            "ECDHE-RSA-AES256-SHA",
            "AES128-GCM-SHA256",
            "AES256-GCM-SHA384"
        ]))
    except ssl.SSLError as e:
        logging.warning(f"Не удалось установить пользовательские шифры: {e}. Используем шифры по умолчанию.")

    try:
        ssl_context.set_ecdh_curve("prime256v1")
    except (ssl.SSLError, ValueError) as e:
        logging.warning(f"Не удалось установить эллиптическую кривую: {e}")

    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    ssl_context.maximum_version = ssl.TLSVersion.TLSv1_3

    tls_connector = aiohttp.TCPConnector(ssl=ssl_context)

    session_kwargs = kwargs.copy()
    session_kwargs['connector'] = tls_connector

    return aiohttp.ClientSession(*args, **session_kwargs)


def replace_first_adjective(text: str) -> str:
    doc = nlp(text)

    tokens = [token.text for token in doc]

    for i, token in enumerate(doc):
        if token.pos_ == 'ADJ':
            word = token.text
            synonyms = get_adjective_synonyms(word)

            if synonyms:
                synonym = random.choice(synonyms)
                if word[0].isupper():
                    synonym = synonym.capitalize()

                tokens[i] = synonym
                break

    return ' '.join(tokens)


def get_adjective_synonyms(word: str) -> List[str]:
    synonyms = set()
    for syn in wordnet.synsets(word.lower(), pos=wordnet.ADJ):
        for lemma in syn.lemmas():
            if lemma.name().lower() != word.lower():
                synonyms.add(lemma.name().replace('_', ' '))
    return list(synonyms)


def get_synonyms(word: str) -> List[str]:
    synonyms = set()
    for syn in wordnet.synsets(word.lower()):
        for lemma in syn.lemmas():
            synonym = lemma.name().replace('_', ' ')
            if synonym.lower() != word.lower():
                synonyms.add(synonym)
    return list(synonyms)


def get_random_synonym_for_word(word: str) -> str:
    all_synonyms = get_synonyms(word)
    return random.choice(all_synonyms) if all_synonyms else word


def get_random_synonym_for_phrase(phrase: str) -> str:
    words = phrase.split(' ')
    new_words = [get_random_synonym_for_word(word) for word in words]
    return ' '.join(new_words)


async def main():
    url = get_url()
    count = get_count()

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    first_file_path = os.path.join(os.path.curdir, "prompt", timestamp + '.csv')
    os.makedirs(os.path.dirname(first_file_path), exist_ok=True)

    second_file_path = os.path.join(os.path.curdir, "metadata", timestamp + '.csv')
    os.makedirs(os.path.dirname(second_file_path), exist_ok=True)

    passed_pages = 0
    index = 1
    browser = None

    try:
        async with AsyncCamoufox(**config.BROWSER_OPTIONS) as browser_instance:
            browser = browser_instance
            main_page = await browser.new_page()

            with open(first_file_path, 'w', newline='', encoding='utf-8') as prompt_file, \
                    open(second_file_path, 'w', newline='', encoding='utf-8') as metadata_file:

                prompt_writer = csv.writer(prompt_file)
                prompt_writer.writerow(['ID', 'Prompt'])

                metadata_writer = csv.writer(metadata_file)
                metadata_writer.writerow(['Filename', 'Title', 'Description', 'Keywords'])

                await main_page.goto(url)

                selector = "xpath=//div[@id='search-results']/div/div/a"
                await main_page.wait_for_selector(selector, timeout=60000)

                cookies = await browser.contexts[0].cookies()
                aiohttp_cookies = {cookie["name"]: cookie["value"] for cookie in cookies}

                session = create_tls_session(
                    headers=headers.copy(),
                    cookies=aiohttp_cookies,
                    max_line_size=8190 * 3,
                    max_field_size=8190 * 3,
                )

                need_wait_selector = False

                while True:
                    if need_wait_selector:
                        await main_page.wait_for_selector(selector, timeout=60000)

                    images = await main_page.query_selector_all(selector)
                    if images:
                        for image in images:
                            try:
                                image_href = await image.get_attribute("href")
                                image_name_elem = await image.query_selector("xpath=/meta[@itemprop='name']")
                                if image_name_elem and image_href:
                                    await image.scroll_into_view_if_needed()
                                    image_href += "?prev_url=detail"
                                    image_name_content = await image_name_elem.get_attribute("content")
                                    if image_name_content:
                                        name = image_name_content.replace('\n', ' ').strip()
                                        name = re.sub(r'\s+', ' ', name).strip()

                                        async with session.get(image_href) as response:
                                            response.raise_for_status()

                                            html = await response.text()
                                            keywords = get_keywords(html)
                                            if not keywords:
                                                logger.error("Теги не были получены: {}".format(image_href))
                                                continue

                                            name_syn = replace_first_adjective(name)

                                            keywords_count = len(keywords)
                                            if keywords_count >= 2:
                                                last_keyword = keywords[-1]
                                                last_keyword_syn = get_random_synonym_for_phrase(last_keyword)
                                                if not last_keyword_syn:
                                                    last_keyword_syn = last_keyword

                                                keywords[-2:] = [last_keyword_syn]
                                            else:
                                                logger.warning(
                                                    f"Количество тегов {keywords_count}, не могу сделать срез 2-х слов")
                                                continue

                                            prompt_writer.writerow([index, name_syn])
                                            metadata_writer.writerow([index, name_syn, name, ''])

                                            logger.info(f"[{index}] {name}")
                                            index += 1
                                    else:
                                        logger.warning(
                                            "Обнаружен элемент изображения без атрибута 'content' или 'href'. Пропускаем")
                            except Exception as e:
                                logger.error(f"Ошибка при обработке: {e}")

                        passed_pages += 1

                    else:
                        logger.warning("На текущей странице не найдено изображений")

                    if 0 < count <= passed_pages:
                        logger.info(f"Достигли заданного количества страниц")
                        break

                    is_complete, next_page_clicked = await goto_next_page(main_page)
                    need_wait_selector = True

                    if is_complete:
                        logger.info("Достигнута последняя доступная страница")
                        break

                    if not next_page_clicked:
                        logger.warning("Не удалось найти или нажать кнопку следующей страницы")
                        break

                logger.warning(f"Пройдено {count} страниц(ы), завершаем работу")
                await browser.close()

    except Exception as e:
        logger.error(f"Произошла ошибка: {e}", exc_info=True)
    finally:
        if browser:
            await browser.close()


def get_keywords(html_content: str) -> list[str] | None:
    sel = Selector(text=html_content)

    script_text = sel.xpath(
        "//body/script[@nonce and contains(text(),'window.__CLIENT_CONFIG__')]/text()").get()
    if not script_text:
        logger.info("Скрипт не найден")
        return None

    pattern = r'"keywords"\s*:\s*\[(.*?)\]'
    match = re.search(pattern, script_text)

    if not match:
        logger.error("Не удалось найти теги в скрипте")
        return None

    keywords_string = match.group(1)
    valid_json_array = f"[{keywords_string}]"
    keywords = json.loads(valid_json_array)

    return keywords


async def goto_next_page(page: Page) -> Tuple[bool, bool]:
    max_retries = 7
    next_page_clicked = False
    is_complete = False
    selector = "xpath=//div[@id='pagination-element']/nav/span[last()]/button"

    for retry in range(max_retries):
        try:
            await page.wait_for_selector(selector, timeout=60000)
            next_page = await page.query_selector(selector)

            if next_page:
                if await next_page.is_disabled():
                    is_complete = True
                    break
                is_attached = await next_page.evaluate("el => el.isConnected")
                if not is_attached:
                    logger.warning(f"Элемент кнопки не прикреплен к DOM, повторная попытка {retry + 1}")
                    continue

                next_page_locator = page.locator(selector)

                await next_page_locator.scroll_into_view_if_needed()
                await next_page_locator.click()

                next_page_clicked = True
                break
            else:
                logger.warning("Кнопка следующей страницы не найдена")
                break

        except Exception as e:
            logger.warning(
                f"Ошибка при попытке перейти на следующую страницу (попытка {retry + 1}): {e}")
            if retry < max_retries - 1:
                await asyncio.sleep(2)
                continue
            else:
                logger.error("Не удалось перейти на следующую страницу после всех попыток")
                break

    return is_complete, next_page_clicked


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Процесс прерван пользователем.")
    except Exception as e:
        logger.critical(f"Произошла непредвиденная ошибка: {e}", exc_info=True)
