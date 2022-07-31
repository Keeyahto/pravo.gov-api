import sys
import json
import logging
import typing
import re
import requests
import urllib.parse
from tqdm import tqdm

import time
from pathlib import Path
from bs4 import BeautifulSoup
import backoff

from api.config import configs
from api.utils.my_logger import Log, create_logger, get_struct_logger

logger = create_logger(__name__)

FROM_DATE = configs.FROM_DATE
TO_DATE = configs.TO_DATE
REGION = configs.REGION
SEARCH_WORD = configs.SEARCH_WORD
GOVERNMENT_BODY = configs.GOVERNMENT_BODY
GOVERNMENT_BODY_CODE = configs.GOVERNMENT_BODY_CODE
TAG_WE_NEED = configs.SEARCH_TAG


class GetMetaInfo:

    def filter_and_get_authors(self, doc_id: str, tag) -> tuple[str, str] | tuple[None,None]:
        """ tag: тэг, без которого просто пропустим документ"""

        @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=4, max_time=30)
        def get_meta_data(doc_id: str) -> BeautifulSoup:
            url_meta = f'http://pravo.gov.ru/proxy/ips/?doc_itself=&vkart=card&nd={doc_id}&page=1&rdk=0&intelsearch=&link_id=0'
            r = requests.get(url_meta).content.decode('cp1251')
            soup = BeautifulSoup(r, 'html.parser')
            return soup

        def check_wanted_tags(meta_data: BeautifulSoup, tag: str = 'назначение') -> bool:
            tags = meta_data.find('div', id='klsl')
            if not tags:
                logger.debug('no tags in --- %s', doc_id)
                return False
            return tag in tags.text.lower()

        def get_doc_date(meta_data: BeautifulSoup) -> str | None:
            head = meta_data.find('div', class_='DC_header').get_text()
            return re.findall(pattern=r'от \d\d.\d\d.\d\d\d\d', string=head)[0].strip('от').strip()

        def get_doc_author(meta_data: BeautifulSoup) -> str | None:
            author = meta_data.find('div', id='pd')
            if author:
                return author.text

        meta = get_meta_data(doc_id)
        if check_wanted_tags(meta, tag):
            return (get_doc_author(meta), get_doc_date(meta))

        return (None, None)


class LinksGetter:

    def __init__(self, logger=None) -> None:
        self.regions_n_number = json.load(open(Path(__file__).parent / 'data' / 'regions_n_their_numbers.json'))
        self.base_url = 'http://pravo.gov.ru/proxy/ips/'
        # сюда прокидывается айди документа, чтобы скачать (120243495)
        self.url_doc_itself = 'http://pravo.gov.ru/proxy/ips/?doc_itself=&nd={doc_id}&page=1&rdk=0&link_id=0#I0'
        # self.download_base_url = 'http://pravo.gov.ru/proxy/ips/?savertf=&link_id=0&nd={doc_id}'
        self.no_tags_counter = 0
        self.logger = get_struct_logger(__name__)
        self.logger = self.logger.bind(region=REGION)

    @Log(__name__)
    def create_url(self)->str:
        """подставляем параметры (DATE, SEARCH_WORD, REGION, GOVERNMENT_BODY ) в url"""
        reg_n = self.regions_n_number.get(REGION)
        if not reg_n:
           raise KeyError('Неверно указано название региона. Допустимые значения:', str(list(self.regions_n_number.keys())))

        base_params = {'bpas': '', 'a3': '', 'a3type': '1', 'a3value': '', 'a6': '', 'a6type': '1', 'a6value': '', 'a15': '', 'a15type': '1', 'a15value': '', 'a7type': '3', 'a7from': '', 'a7to': '', 'a7date': '', 'a8': '', 'a8type': '1', 'a1': '', 'a0': '', 'a16': '', 'a16type': '1', 'a16value': '', 'a17': '', 'a17type': '1', 'a17value': '', 'a4': '', 'a4type': '1', 'a4value': '', 'a23': '', 'a23type': '1', 'a23value': '', 'textpres': '', 'sort': '7', 'x': '48', 'y': '8', 'lstsize': '200', 'start': '0'}


        user_params = {'a7type':'4','bpas':reg_n, "a6":GOVERNMENT_BODY_CODE,'a6value':GOVERNMENT_BODY, 'a7from':FROM_DATE, 'a7to':TO_DATE,'a0':SEARCH_WORD}
        base_params.update(user_params)
        encoded_params = urllib.parse.urlencode(base_params, encoding='cp1251')
        url = self.base_url + '?searchlist=&' + encoded_params
        print(url)
        'http://pravo.gov.ru/proxy/ips/?searchres=&bpas=cd00000&a3=&a3type=1&a3value=&a6=102000066&a6type=1&a6value=%CF%F0%E0%E2%E8%F2%E5%EB%FC%F1%F2%E2%EE&a15=&a15type=1&a15value=&a7type=3&a7from=&a7to=&a7date=01.01.2022&a8=&a8type=1&a1=&a0=&a16=&a16type=1&a16value=&a17=&a17type=1&a17value=&a4=&a4type=1&a4value=&a23=&a23type=1&a23value=&textpres=&sort=7&x=62&y=9'
        return url

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=4, max_time=30)
    @Log(__name__)
    def get_pages_to_parse(self, url) -> list[str]:
        """вытягиваем ссылки на страницы. на каждой по 200 документов"""
        time.sleep(3)
        r = requests.get(url).content.decode('cp1251')
        soup = BeautifulSoup(r,'html.parser')
        links_raw = soup.find_all('div', id='search_results_list_params_full')[0].find_all('a')
        page_links = (e.attrs.get('href') for e in links_raw)
        page_links = [self.base_url + link for link in page_links]
        self.logger.debug(f'Found {len(page_links)} pages with docs!')
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
    def get_links(self, tag_we_need) -> dict[str,dict[str,str]]:
        initial_url = self.create_url()
        pages_to_parse = self.get_pages_to_parse(initial_url)
        self.logger.debug('Getting links from pages')
        if not pages_to_parse: # если одна страница и пагинации нет
            docs_links = self.get_page_docs(initial_url)
        else:
            # ссылки на все доки всех страниц
            docs_links = [self.get_page_docs(page) for page in tqdm(pages_to_parse)]
            docs_links = sum(docs_links, [])
        # взяли только айди доков
        doc_ids = [urllib.parse.parse_qs(link).get('nd')[0] for link in docs_links]#[:100]
        self.logger.debug(f'Found {len(doc_ids)} links on all pages')

        # получаем метаданные и фильтруем  документы, в которых нет тэга
        doc_ids_with_authors = {}
        self.logger.debug("Getting documents' meta-data")
        for doc_id in tqdm(doc_ids):
            # зашли на страницу с метаданными. если тэг подходит, находим автора и отдаем его.
            try:
                author, date = self.filter_and_get_authors(doc_id, tag_we_need)
                if not author:
                    self.no_tags_counter += 1

            except Exception as ex:
                tb = sys.exc_info()[-1]
                self.logger = self.logger.bind(doc_id=doc_id)
                self.logger.error(str(tb.with_traceback()))
                self.logger.unbind('doc_id')
                author = False
            if author:
                # вставили айди доков в ссылку для скачивания
                download_link = self.url_doc_itself.format(doc_id=doc_id)
                doc_ids_with_authors[doc_id] = {'author':author,'link':download_link, 'date':date}
        return doc_ids_with_authors

    def download_links(self, destination_path:Path)->list[str]:
        links_with_info = self.get_links(tag_we_need=TAG_WE_NEED)
        with open(destination_path, 'w', encoding='utf-8') as f:
            json.dump(links_with_info, f, ensure_ascii=False)
            # self.logger.debug(f'сохранили {len(links_with_info)} ссылок!')
            '''  
            self.logger.debug(f'сохранили {len(links_with_info)} ссылок!')
            TypeError: _make_filtering_bound_logger.<locals>.make_method.<locals>.meth() takes 2 positional arguments but 3 were given
            
            '''
            # self.logger.debug('отфильтровали с неподходящими тэгами %s',self.no_tags_counter )
            print('сохранили ', len(links_with_info), ' ссылок!')
            print('отфильтровали с неподходящими тэгами - ', self.no_tags_counter)
        return [links_with_info[e]['link'] for e in links_with_info]

if __name__ == '__main__':
    # links_getter = LinksGetter()
    # doc_id = '109230530'
    # print(links_getter.filter_and_get_authors(109230530))
    print(bool((None,None)))
    # print(links_getter.create_url())
    #
    # download_links = links_getter.download_links(

    #     destination_path=configs.LINKS_N_FILES_INFO, tag_we_need=configs.SEARCH_TAG)
    # print(download_links)

    # doc_id = '603123276'
    # doc_id='603039028'
    # url_meta = f'http://pravo.gov.ru/proxy/ips/?doc_itself=&vkart=card&nd={doc_id}&page=1&rdk=0&intelsearch=&link_id=0'
    # r = requests.get(url_meta).content.decode('cp1251')
    # soup = BeautifulSoup(r, 'html.parser')
    # meta = get_meta_data(doc_id)

# try:
    #     raise ValueError('aa')
    # except Exception as ex:
    #     import traceback
    #     tb = sys.exc_info()[-1]

        # tb = sys.exc_info()
        # print(tb)
        # traceback.extract_tb()


    # print(links_getter.url_doc_itself.format(doc_id='603123276'))


    # url_doc_itself = f'http://pravo.gov.ru/proxy/ips/?doc_itself=&nd={doc_id}&page=1&rdk=0&intelsearch=%CD%E0%E7%ED%E0%F7%E8%F2%FC&link_id=0#I0'

    #
    # # r = requests.get(url_meta).content.decode('cp1251')
    # r = requests.get(url_doc_itself).content.decode('cp1251')
    #
    # soup = BeautifulSoup(r, 'html.parser')
    # print(soup.get_text('\n'))
    #

    # print(soup.find('div', id='pd').text)


# url_doc_itself = f'http://pravo.gov.ru/proxy/ips/?doc_itself=&nd={doc_id}&page=1&rdk=0&intelsearch=%CD%E0%E7%ED%E0%F7%E8%F2%FC&link_id=0#I0'
    # # print(url_doc_itself)
    # # r = requests.get(url_meta).content.decode('cp1251')
    # r = requests.get(url_meta).content.decode('cp1251')
    #
    # soup = BeautifulSoup(r,'html.parser')
    # # print(r)
    # print(get_meta_data(doc_id))
    # with open('test.html', 'w') as f:
    #     f.write(r)
    #     print(r)

