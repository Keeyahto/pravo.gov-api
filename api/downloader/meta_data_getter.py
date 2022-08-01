from bs4 import BeautifulSoup
from pathlib import Path
import json

class MetaGetter:
    '''
    ходит в файл с метаданными meta_data_file и вставляет инфу в тело документа
    '''
    
    def __init__(self, meta_data_file:str|Path) -> None:
        with open(meta_data_file, encoding='utf-8') as f:
            self.meta_data = json.load(f)

    def insert_meta_in_html(self, html:BeautifulSoup, doc_id:str)->str:
        doc_meta = self.meta_data.get(doc_id)
        if not doc_meta:
            return html

        new_tag = html.new_tag(
            "my_meta", **doc_meta)

        html.find('meta').append(new_tag)
        return str(html)
