"""
В классе Configs указываются все основные настройки для скачивания документов.

"""

import json
from pathlib import Path

from pydantic import BaseSettings, validator


class Configs(BaseSettings):
    '''
        Параметры поиска:

            Для поиска по базе необходимо указать хотя бы одну из следующих групп параметров: 

            1. 
                SEARCH_WORD (str | None): слово, которое должно быть в тексте документа
                SEARCH_TAG (str | None): тэг, который должен быть в мета-данных документа

            2.
                FROM_DATE (str | None): с какой даты
                TO_DATE (str | None): по какую

            3.
                Поиск по региональным базам:
                    REGION (str | None): <название субъекта>
                
                Поиск по федеральным базам:
                    REGION (str | None) = "РФ"
                    FEDERAL_GOVERNMENT_BODY (str | None) = <название органа> (e.g. Президент, Правительство)
                
                Полный список органов и регионов в /api_data или на https://github.com/kbondar17/pravo-gov-API         


        Сохранение документов:
            SAVE_FORMAT: txt - только текст | html с html-тэгами
            RAW_FILES_FOLDER: место для сохранения документов (по умолчанию data/регион/raw_files)
            Название файла - id документа на портале.
            LINKS_N_FILES_INFO: информация о документе - дата, тэги, подписавший, ссылка (по умолнчанию links/регион/files_n_links.json)

            ├── data/
            │   └── Калужская область/
            │       ├── links/
            │       │   └── files_n_links.json 
            │       └── raw_files/
            |           └──1234566788.html

    '''

    SEARCH_WORD: str | None = 'назначить' #
    SEARCH_TAG: str | None = 'назначение' #
    FROM_DATE: str | None = '01.01.2005'
    TO_DATE: str | None = '01.08.2022'

    REGION: str | None = 'Московская область' #Свердловская область
    REGION_CODE: str = None # 
    FEDERAL_GOVERNMENT_BODY = ''  # Президент
    FEDERAL_GOVERNMENT_BODY_CODE: int = 0

    SAVE_FORMAT = 'html'

    # Папки
    DATA_FOLDER: Path = Path(__file__).parents[1] / 'data'
    REGION_FOLDER = DATA_FOLDER / REGION

    RAW_FILES_FOLDER: Path = DATA_FOLDER / REGION / 'raw_files'
    LINKS_FOLDER: Path = DATA_FOLDER / REGION / 'links'
    LINKS_N_FILES_INFO = LINKS_FOLDER / 'files_n_links.json'

    LINKS_FAILED_AT_DOWNLOADING = LINKS_FOLDER / 'failed_links.json'

    # Прочее
    LOGGING_LEVEL: str = 'ERROR'
    MAIN_LOG_FILE: str = 'api/logs/main.json'


    @validator('DATA_FOLDER', 'RAW_FILES_FOLDER', 'LINKS_FOLDER')
    def create_folders(cls, v: Path, values):
        '''создаем папки, если их нет'''
        v.mkdir(exist_ok=True, parents=True)
        return v

    @validator('LINKS_N_FILES_INFO')
    def create_files_if_not_exist(cls, v: Path, values, **kwargs):
        if not v.exists():
            with open(v, 'w', encoding='utf-8') as f:
                ...
        return v

    @validator('FEDERAL_GOVERNMENT_BODY', pre=True)
    def translate_human_to_code(cls, v, values):
        '''находит айди учреждения. напр - Президент == '102000070' '''
        if not v:
            return ''
        with open('api/api_data/gov_bodies_n_their_codes.json', encoding='utf-8') as f:
            gov_bodies_codes = json.load(f)
            if v in gov_bodies_codes.keys():
                values['FEDERAL_GOVERNMENT_BODY_CODE'] = gov_bodies_codes[v]
                return v
            raise KeyError(f'неправильное написание учреждения. допустимые варианты:\
                           {list(gov_bodies_codes.keys())}')

    @validator('REGION_CODE')
    def get_region_code(cls, v, values):
        '''находит айди региона. напр - Брянская область == 'r013200' '''
        if not values['REGION']:
            return 'cd00000'
        with open('api/api_data/regions_n_their_numbers.json', encoding='utf-8') as f:
            try:
                codes = json.load(f)
                region_code = codes[values['REGION']]
                return region_code
            except KeyError:
                raise KeyError(
                    f'''{values['REGION']} направильно указан регион. допустимые значения {list(codes.keys())}''')


    @validator('MAIN_LOG_FILE')
    def get_abs_path(cls, v, values):
        return Path(v).absolute()


configs = Configs()
