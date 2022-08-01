import asyncio
import json
import time
import urllib
from pathlib import Path
from random import uniform
import aiohttp

from bs4 import BeautifulSoup
from api.config import configs
from api.downloader.meta_data_getter import MetaGetter
from api.utils.my_logger import get_struct_logger


FORMAT = configs.SAVE_FORMAT


class FilesDownloader:
    """скачивает и сохраняет файлы по ссылке"""

    def __init__(self, result_folder: Path, links_to_load: list[str], failed_links_file: Path | str, meta_data_file:str|Path) -> None:
        """принимает ссылки на доки"""
        self.result_folder = Path(result_folder)
        self.filelogger = get_struct_logger(__name__)
        self.links = links_to_load
        self.downloaded = 0
        self.failed_links_file = failed_links_file
        if meta_data_file:
            self.meta_getter = MetaGetter(meta_data_file=meta_data_file)

    def _get_file_id(self, url) -> str:
        return urllib.parse.parse_qs(url).get('nd')[0]

    def save_document(self, file_name, doc_body:str, format):
        if format not in ['html', 'txt']:
            raise ValueError(f'допустимые форматы: txt, html')
        file_path = self.result_folder / (file_name + f'.{format}')
        
        soup = BeautifulSoup(doc_body, 'html.parser')
        
        if format == 'html' and self.meta_getter:
            # вставялем метаданные
            doc_body = self.meta_getter.insert_meta_in_html(html=soup, doc_id=file_name) 
        
        if format == 'txt':
            raw_text = soup.get_text('|||', strip=True).split('|||')
            raw_text = [e.replace('\xa0', ' ') for e in raw_text]
            doc_body = '\n'.join(raw_text).replace('Complex', '')
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(doc_body)
            self.downloaded += 1

    def _save_html_to_result_folder(self, file_name: str, html: str):
        file_path = self.result_folder / file_name
        with open(file_path, 'w', encoding='cp1251') as f:
            f.write(html)
            self.downloaded += 1

    def _save_failed_links(self, failed_links: list[str]):
        with open(self.failed_links_file, 'w', encoding='utf-8') as f:
            json.dump(failed_links, f, ensure_ascii=False)

    async def download_links(self, links: list[str]) -> list[str | None]:
        failed_links = []
        async with aiohttp.ClientSession() as session:
            for link in links:  
                doc_id = self._get_file_id(link)
                file_name = doc_id  
                try:
                    async with session.get(link) as response:
                        if response.status == 200:
                            html = await response.text()
                            self.save_document(
                                file_name=file_name, doc_body=html, format=FORMAT)
                            filelogger = self.filelogger.bind(
                                filename=file_name)
                            filelogger.debug('doc downloaded successfully')
                            time.sleep(uniform(0.2, 0.6))

                        else:
                            if link not in failed_links:
                                failed_links.append(link)
                            filelogger = self.filelogger.bind(
                                filename=file_name, http_eror=response.status)
                            filelogger.error('http_error')

                except aiohttp.ClientConnectorError as err:
                    filelogger = self.filelogger.bind(
                        filename=file_name, eror=str(err))
                    filelogger.error('connection_error')
                    if link not in failed_links:
                        failed_links.append(link)
        return failed_links

    def go(self) -> None:
        loop = asyncio.get_event_loop()

        failed = loop.run_until_complete(self.download_links(self.links))
        if failed:
            failed_in_second_attempt = loop.run_until_complete(
                self.download_links(failed))
            self.filelogger.error(
                f'not downloaded after second attempt {failed_in_second_attempt}')
            self._save_failed_links(failed)

        self.filelogger.debug(
            f'Dowloaded {self.downloaded} / {len(self.links)}')
