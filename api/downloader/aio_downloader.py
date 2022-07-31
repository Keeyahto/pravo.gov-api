import asyncio
import json
import time
import urllib
from pathlib import Path
from random import uniform

import aiohttp
from api.config import configs
from api.utils.my_logger import get_struct_logger
from bs4 import BeautifulSoup

FORMAT = configs.SAVE_FORMAT

class FilesDownloader:
    """скачивает и сохраняет файлы по ссылке"""
    
    def __init__(self, result_folder:Path, links_to_load:list[str], logs_file:Path|str, failed_links_file:Path|str) -> None:
        """принимает ссылки на доки"""
        self.result_folder = Path(result_folder)
        self.filelogger = get_struct_logger(__name__)
        self.links = links_to_load
        self.ok = 0
        self.failed_links_file = failed_links_file

    def _get_file_id(self, url)->str:
        return urllib.parse.parse_qs(url).get('nd')[0]


    def save_document(self, file_name, doc_body, format):
        if format not in ['html','txt']:
            raise ValueError(f'допустимые форматы: txt, html')
        file_path = self.result_folder / (file_name + f'.{format}')
        if format == 'txt':
            soup = BeautifulSoup(doc_body, 'html.parser')
            raw_text = soup.get_text('|||', strip=True).split('|||')
            raw_text = [e.replace('\xa0', ' ') for e in raw_text]
            doc_body = '\n'.join(raw_text).replace('Complex','')
        with open(file_path, 'w') as f:
            f.write(doc_body)
            self.ok += 1

    def _save_html_to_result_folder(self, file_name:str, html:str):
        file_path = self.result_folder / file_name
        with open(file_path,'w') as f:
            f.write(html)
            self.ok += 1

    def _save_failed_links(self, failed_links:list[str]):
        with open(self.failed_links_file,'w', encoding='utf-8') as f:
            json.dump(failed_links, f, ensure_ascii=False)

    async def download_links(self, links:list[str])->list[str|None]:
        failed_links = []
        async with aiohttp.ClientSession() as session:
            for link in links: #[:10]
                doc_id = self._get_file_id(link)
                file_name = doc_id #+ '.html'
                try:
                    async with session.get(link) as response:
                        if response.status == 200:
                            html = await response.text()
                            self.save_document(file_name=file_name,doc_body=html, format=FORMAT)
                            # self._save_html_to_result_folder(file_name=file_name, html=html)
                            filelogger = self.filelogger.bind(filename=file_name)
                            filelogger.debug('doc downloaded successfully')
                            time.sleep(uniform(0.2, 0.6))

                        else:
                            if link not in failed_links:
                                failed_links.append(link)
                            filelogger = self.filelogger.bind(filename=file_name, http_eror=response.status)
                            filelogger.error('http_error')

                except aiohttp.ClientConnectorError as err:
                    filelogger = self.filelogger.bind(filename=file_name, eror=str(err))
                    filelogger.error('connection_error')
                    if link not in failed_links:
                        failed_links.append(link)
        return failed_links

    def go(self) -> None:
        loop = asyncio.get_event_loop()

        failed = loop.run_until_complete(self.download_links(self.links))
        if failed:
            failed_in_second_attempt = loop.run_until_complete(self.download_links(failed))
            self.filelogger.error(f'not downloaded after second attempt {failed_in_second_attempt}')
            self._save_failed_links(failed)

        self.filelogger.debug(f'Dowloaded {self.ok} / {len(self.links)}')


if __name__ == '__main__':
    loader = FilesDownloader()
        

# async def download_sites(sites)->list[str]:
#     async with aiohttp.ClientSession() as session:
#       for site in sites:
#         try:
#           async with session.get(site) as response:
#             if response.status == 200:
#             #   print("Status:", response.status)
#             #   print("Content-type:", response.headers['content-type'])
#                 html = await response.text()
#                 print("Body:", html[:15], "...")
#                 # time.sleep(uniform(0.2, 0.6))
#             else:
#                 if site not in failed:
#                     failed.append(site)
#                 print('здесь логируем и добавляем в список failed')
#                 print(response.status)
#         except aiohttp.ClientConnectorError as e:
#             if site not in failed:
#                 failed.append(site)
#             # print()
#             # print('здесь логируем и добавляем в список failed')
#             print('Connection Error', str(e), site)

