import json

from pydantic import BaseSettings, validator
from pathlib import Path

from api.decree_parser.tools.name_parser import Gender


class Configs(BaseSettings):
    '''
    Настройки поиска и парсинга документов.
    Регион указывается в формате: "Владимирская область"
    Для федеральных органов - "РФ".
    Все регионы перечислены в decree_parser/data/regions_n_links.json
    GOVERNMENT_BODY: федеральные органы, доступно только в "РФ". e.g "Президент", "Министерство внутренних дел"
    '''

    # Параметры поиска
    SEARCH_WORD: str = 'назначить' # может быть пустым
    SEARCH_TAG: str = 'назначение' # отфильтрует документы без этого тэга
    FROM_DATE: str = '01.01.2010'
    TO_DATE: str = '01.07.2020'

    REGION: str = 'Калужская область'
    REGION_CODE:str = None # берется автоматически из /api_data/gov_bodies_n_their_codes.json
    GOVERNMENT_BODY = '' # Президент

    # Формат сохранения
    SAVE_FORMAT = 'html' # txt | html

    # Папки
    DATA_FOLDER: Path = Path(__file__).parents[1] / 'data'
    REGION_FOLDER = DATA_FOLDER / REGION

    RAW_FILES_FOLDER: Path = DATA_FOLDER / REGION / 'raw_files'
    LINKS_FOLDER: Path = DATA_FOLDER / REGION / 'links'
    LINKS_N_FILES_INFO = LINKS_FOLDER / 'files_n_links.json'

    LINKS_FAILED_AT_DOWNLOADING = LINKS_FOLDER / 'failed_links.json'

    # Прочее
    LOGGING_LEVEL: str = 'ERROR'
    DOWNLOADING_FILES_LOGS = RAW_FILES_FOLDER / 'downloading_logs.json'
    GOVERNMENT_BODY_CODE: int = 0 # айди учреждения. полный список - gov_bodies_n_their_codes.json
    MAIN_LOG_FILE:str = 'logs/main.log'

    @validator('DATA_FOLDER', 'RAW_FILES_FOLDER', 'LINKS_FOLDER')
    def create_folders(cls, v:Path, values, **kwargs):
        '''создаем папки, если их нет'''
        v.mkdir(exist_ok=True, parents=True)
        return v

    @validator('LINKS_N_FILES_INFO')
    def create_files_if_not_exist(cls, v: Path, values, **kwargs):
        if not v.exists():
            with open(v, 'w') as f:
                ...
        return v

    @validator('GOVERNMENT_BODY', pre=True)
    def translate_human_to_code(cls, v, values):
        '''находит айди учреждения. напр - Президент == '102000070' '''
        if not v:
            return ''
        with open('api_data/gov_bodies_n_their_codes.json', encoding='utf-8') as f:
            gov_bodies_codes = json.load(f)
            if v in gov_bodies_codes.keys():
                values['GOVERNMENT_BODY_CODE'] = gov_bodies_codes[v]
                return v
            else:
                raise KeyError(f'неправильное написание учреждения. допустимые варианты: {list(gov_bodies_codes.keys())}')

    @validator('REGION_CODE')
    def get_region_code(cls, v, values):
        '''находит айди региона. напр - Брянская область == 'r013200' '''
        if not values['REGION']:
            return ''
        with open('api_data/regions_n_their_numbers.json', encoding='utf-8') as f:
            try:
                codes = json.load(f)
                region_code = codes[values['REGION']]
                return region_code
            except KeyError:
                raise KeyError(f'''{values['REGION']} направильно указан регион. допустимые значения {list(codes.keys())}''')

        # if not v:
        #     return ''
        # with open('api_data/regions_n_their_numbers.json', encoding='utf-8') as f:
        #     codes = json.load(f)
        #     try:
        #         values['REGION_CODE'] = codes[v]
        #         return v
        #     except KeyError:
        #         raise KeyError(f'направильно указан регион. допустимые значения {list(codes.keys())}')

    @validator('MAIN_LOG_FILE')
    def get_abs_path(cls, v, values):
        return Path(v).absolute()

configs = Configs()

