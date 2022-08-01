import json

from api.config import configs
from api.downloader.aio_downloader import FilesDownloader
from api.utils.my_logger import get_struct_logger
from api.links_getter import LinksGetter

REGION_CODE = configs.REGION_CODE
MAIN_LOG_FILE = configs.MAIN_LOG_FILE

if __name__ == '__main__':
    my_logger = get_struct_logger(__name__)
    my_logger.msg('стартуем')

    links_getter = LinksGetter(region_code=REGION_CODE)
    download_links = links_getter.download_links(
        destination_path=configs.LINKS_N_FILES_INFO)

    files_loader = FilesDownloader(
        result_folder=configs.RAW_FILES_FOLDER,
        links_to_load=download_links,
        failed_links_file=configs.LINKS_FAILED_AT_DOWNLOADING,
        meta_data_file=configs.LINKS_N_FILES_INFO
    )
    files_loader.go()

