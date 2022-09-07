import json
import re
import sys
import urllib.parse
from pathlib import Path
import requests
import time
from urllib.error import HTTPError


import backoff
from bs4 import BeautifulSoup
from tqdm import tqdm

from api.config import configs
from api.links_getter.models import DocInfo
from api.utils.my_logger import Log, get_struct_logger

FROM_DATE = configs.FROM_DATE
TO_DATE = configs.TO_DATE
REGION = configs.REGION
SEARCH_WORD = configs.SEARCH_WORD
GOVERNMENT_BODY = configs.FEDERAL_GOVERNMENT_BODY
GOVERNMENT_BODY_CODE = configs.FEDERAL_GOVERNMENT_BODY_CODE
TAG_WE_NEED = configs.SEARCH_TAG

logger = get_struct_logger(__name__, configs.MAIN_LOG_FILE)


class GetMetaInfo:
    '''получает мета-данные о доке (дата, тэги, подписавший, ссылка)'''

    def __init__(self, logger):
        self.logger = logger
    #0001202208040007
    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=4, max_time=30)
    def _get_raw_meta_data(self, doc_id) -> str:  # html
        url_meta = f'http://pravo.gov.ru/proxy/ips/?doc_itself=&vkart=card&nd={doc_id}\
                    &page=1&rdk=0&intelsearch=&link_id=0'
        r = requests.get(url_meta).content.decode('cp1251')
        return r

    def get_tags(self, soup: BeautifulSoup) -> list[str] | list[None]:
        tags = soup.find('div', id='klsl') 
        if not tags:
            return []
        return [tag.strip() for tag in tags.text.lower().split(',')]

    @staticmethod
    def get_doc_date(soup: BeautifulSoup) -> str | None:
        head = soup.find('div', class_='DC_header').get_text()
        return re.findall(pattern=r'от \d\d.\d\d.\d\d\d\d', string=head)[0].strip('от').strip()

    @staticmethod
    def get_doc_author(soup: BeautifulSoup) -> str | None:
        author = soup.find('div', id='pd')
        if author:
            return author.text

    def get_doc_meta_info(self, doc_id) -> dict[str, str | None]:
        try:
            raw_meta = self._get_raw_meta_data(doc_id=doc_id)
            soup = BeautifulSoup(raw_meta, 'html.parser')
            tags = self.get_tags(soup)
            author = self.get_doc_author(soup)
            date = self.get_doc_date(soup)
            return {'doc_id': doc_id, 'tags': tags, 'author': author, 'date': date, 'region':configs.REGION}
        except Exception as ex:
            tb = sys.exc_info()[-1]
            self.logger.error(f'{ex}\n\n{tb}\ndoc_id --- {doc_id}')


class LinksGetter:
    '''сохраняет ссылки и айди документов, подходящих под параметры поиска'''

    def __init__(self, region_code: str) -> None:
        self.region_code = region_code
        self.base_url = 'http://pravo.gov.ru/proxy/ips/'

        # сюда прокидывается айди документа, чтобы скачать (напр. 120243495)
        self.url_doc_itself = 'http://pravo.gov.ru/proxy/ips/?doc_itself=&nd={doc_id}&page=1&rdk=0&link_id=0#I0'
        self.no_tags_counter = 0
        self.meta_info_getter = GetMetaInfo(logger=logger)
        self.logger = logger

    @Log(__name__)
    def create_url(self) -> str:
        """подставляем параметры (DATE, SEARCH_WORD, REGION, GOVERNMENT_BODY ) в url"""

        base_params = {'bpas': '', 'a3': '', 'a3type': '1', 'a3value': '', 'a6': '', 'a6type': '1', 'a6value': '',
                       'a15': '', 'a15type': '1', 'a15value': '', 'a7type': '3', 'a7from': '', 'a7to': '', 'a7date': '',
                       'a8': '', 'a8type': '1', 'a1': '', 'a0': '', 'a16': '', 'a16type': '1', 'a16value': '', 'a17': '',
                       'a17type': '1', 'a17value': '', 'a4': '', 'a4type': '1', 'a4value': '', 'a23': '', 'a23type': '1',
                       'a23value': '', 'textpres': '', 'sort': '7', 'x': '48', 'y': '8', 'lstsize': '200', 'start': '0'}

        user_params = {'a7type': '4', 'bpas': self.region_code, "a6": GOVERNMENT_BODY_CODE,
                       'a6value': GOVERNMENT_BODY, 'a7from': FROM_DATE, 'a7to': TO_DATE, 'a0': SEARCH_WORD}

        base_params.update(user_params)
        encoded_params = urllib.parse.urlencode(base_params, encoding='cp1251')
        url = self.base_url + '?searchlist=&' + encoded_params
        return url

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=4, max_time=30)
    @Log(__name__)
    def get_pages_to_parse(self, url) -> list[str]:
        """вытягиваем ссылки на страницы. на каждой по 200 документов"""
        # time.sleep(3)
        print(url)
        r = requests.get(url).content.decode('cp1251')
        if not r:
            raise HTTPError(url, 404, 'Документы по запросу не найдены. Попробуй расширить поиск.', hdrs='aa', fp='')
        soup = BeautifulSoup(r, 'html.parser')
        
        
        links_raw = soup.find_all('div', id='search_results_list_params_full')[
            0].find_all('a')
        page_links = (e.attrs.get('href') for e in links_raw)
        page_links = [self.base_url + link for link in page_links]
        self.logger.debug(
            f'Found {len(page_links) if len(page_links) > 0 else 1} pages with docs!')
        return page_links

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=4, max_time=30)
    @Log(__name__)
    def get_page_docs(self, page_url: str) -> list[str]:
        """вытаскиваем все ссылки на документы со страницы"""
        r = requests.get(page_url).content.decode('cp1251')
        soup = BeautifulSoup(r, 'html.parser')
        # переключились на нужный iframe
        iframe_src = soup.select_one("#list").attrs["src"]
        # подключились к нему
        r = requests.get(self.base_url + iframe_src).content.decode('cp1251')
        soup = BeautifulSoup(r, 'html.parser')
        doc_links = soup.find_all('div', class_='l_link')
        doc_links = (e.find('a').attrs.get('href') for e in doc_links)
        doc_links = [self.base_url + link for link in doc_links]
        return doc_links

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=4, max_time=30)
    @Log(__name__)
    def _get_all_links(self, initial_url) -> list[str] | None:
        pages_to_parse = self.get_pages_to_parse(initial_url)
        self.logger.debug('Getting links from pages')
        if not pages_to_parse:  # если одна страница и пагинации нет
            docs_links = self.get_page_docs(initial_url)
        else:
            # ссылки на все доки всех страниц
            docs_links = [self.get_page_docs(page)
                          for page in tqdm(pages_to_parse)]
            docs_links = sum(docs_links, [])
        # взяли только айди доков
        doc_ids = [urllib.parse.parse_qs(link).get(
            'nd')[0] for link in docs_links]  # [:100]
        self.logger.debug(f'Found {len(doc_ids)} links on all pages')
        return doc_ids

    def _filter_docs_without_tags(self, docs: list[DocInfo], tag_we_need) -> list[DocInfo]:
        filtered = []
        for doc in docs:
            if tag_we_need in doc.tags:
                filtered.append(doc)
            else:
                self.no_tags_counter += 1
        return filtered

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=4, max_time=30)
    @Log(__name__)
    def get_links(self, tag_we_need='') -> dict[str, dict]:
        initial_url = self.create_url()
        docs_ids = self._get_all_links(initial_url)
        
        docs_with_meta_data = [DocInfo(
            **self.meta_info_getter.get_doc_meta_info(doc_id)) for doc_id in tqdm(docs_ids)]
        
        # получаем метаданные и фильтруем  документы, в которых нет тэга
        if tag_we_need:
            docs_with_meta_data = self._filter_docs_without_tags(
                docs_with_meta_data, tag_we_need)

        for doc in docs_with_meta_data:
            doc.url = self.url_doc_itself.format(doc_id=doc.doc_id)
        dic = {}
        for doc in docs_with_meta_data:
            dic[doc.doc_id] = doc.dict()
        return dic

    def download_links(self, destination_path: Path) -> list[str]:
        links_with_info = self.get_links(tag_we_need=TAG_WE_NEED)

        with open(destination_path, 'r', encoding='utf-8') as f:
            try:
                existing_links_info = json.load(f)
            except json.decoder.JSONDecodeError:
                existing_links_info = {}

        existing_links_info.update(links_with_info)

        with open(destination_path, 'w', encoding='utf-8') as f:
            json.dump(existing_links_info, f, ensure_ascii=False)
            self.logger.debug(f'сохранили {len(links_with_info)} ссылок!')

        only_links = links_with_info.values()
        return [doc['url'] for doc in only_links]


if __name__ == '__main__':
    links_getter = LinksGetter(region_code=REGION)
    doc_id = '109230530'
    links_getter.download_links(Path(__file__).parent/'test.json')
