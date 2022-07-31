from api.config import configs
import json
from links_getter import LinksGetter
from api.downloader.aio_downloader import FilesDownloader
from api.decree_parser.decree_parser import Parser
from api.utils.my_logger import get_struct_logger
from api.config import configs

REGION_CODE = configs.REGION_CODE
MAIN_LOG_FILE = configs.MAIN_LOG_FILE

if __name__ == '__main__':
    my_logger = get_struct_logger(__name__)
    my_logger.msg('стартуем')
    # доки, которые не удалось скачать - в отдельный файл
    # files_loader_logger = get_struct_logger(log_file=configs.DOWNLOADING_FILES_LOGS)

    links_getter = LinksGetter(region_code=REGION_CODE)
    download_links = links_getter.download_links(
        destination_path=configs.LINKS_N_FILES_INFO)

    '''когда не хотим запускать links_getter'''
    # links_file = configs.LINKS_N_FILES_INFO
    # with open(links_file, encoding='utf-8') as f:
    #     download_links = json.load(f)
    #     download_links = [download_links[e]['url'] for e in download_links][:20]

    # files_loader = FilesDownloader(
    #                                result_folder=configs.RAW_FILES_FOLDER, links_to_load=download_links,
    #                                 failed_links_file=configs.LINKS_FAILED_AT_DOWNLOADING, logs_file=configs.DOWNLOADING_FILES_LOGS,
    # )
    # files_loader.go()

    #
    # if configs.TO_PARSE:
    #
    #     # parsing_logger = get_struct_logger(configs.PARSING_LOGGER_FILE)
    #     parser = Parser(word_to_search=configs.SEARCH_WORD,
    #                       files_n_links_info=configs.LINKS_N_FILES_INFO)
    #
    #     parser.parse_folder(folder=configs.RAW_FILES_FOLDER,
    #                         parsing_results_file=configs.PARSING_RESULTS_FILE)
    #


