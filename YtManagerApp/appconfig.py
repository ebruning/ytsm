import logging
import os
import os.path
from shutil import copyfile

from django.conf import settings as dj_settings
from django.contrib.auth.models import User

from .models import UserSettings
from .utils.customconfigparser import ConfigParserWithEnv

__SETTINGS_FILE = 'config.ini'
__LOG_FILE = 'log.log'
__LOG_FORMAT = '%(asctime)s|%(process)d|%(thread)d|%(name)s|%(filename)s|%(lineno)d|%(levelname)s|%(message)s'

__DEFAULT_SETTINGS = {
    'global': {
        'YouTubeApiKey': 'AIzaSyBabzE4Bup77WexdLMa9rN9z-wJidEfNX8',
        'SynchronizationSchedule': '0 * * * *',
        'SchedulerConcurrency': '2',
    },
    'user': {
        'MarkDeletedAsWatched': 'True',
        'DeleteWatched': 'True',
        'AutoDownload': 'True',
        'DownloadMaxAttempts': '3',
        'DownloadGlobalLimit': '',
        'DownloadSubscriptionLimit': '5',
        'DownloadOrder': 'playlist_index',
        'DownloadPath': '${env:USERPROFILE}${env:HOME}/Downloads',
        'DownloadFilePattern': '${channel}/${playlist}/S01E${playlist_index} - ${title} [${id}]',
        'DownloadFormat': 'bestvideo+bestaudio',
        'DownloadSubtitles': 'True',
        'DownloadAutogeneratedSubtitles': 'False',
        'DownloadSubtitlesAll': 'False',
        'DownloadSubtitlesLangs': 'en,ro',
        'DownloadSubtitlesFormat': '',
    }
}

log_path = os.path.join(dj_settings.BASE_DIR, 'config', __LOG_FILE)
settings_path = os.path.join(dj_settings.BASE_DIR, 'config', __SETTINGS_FILE)
settings = ConfigParserWithEnv(defaults=__DEFAULT_SETTINGS, allow_no_value=True)


def __initialize_logger():
    log_level_str = settings.get('global', 'LogLevel', fallback='INFO')

    try:
        log_level = getattr(logging, log_level_str)
        logging.basicConfig(filename=log_path, level=log_level, format=__LOG_FORMAT)

    except AttributeError:
        logging.basicConfig(filename=log_path, level=logging.INFO, format=__LOG_FORMAT)
        logging.warning('Invalid log level "%s" in config file.', log_level_str)


def initialize_app_config():
    load_settings()
    __initialize_logger()
    logging.info('Application started!')


def load_settings():
    if os.path.exists(settings_path):
        with open(settings_path, 'r') as f:
            settings.read_file(f)


def save_settings():
    if os.path.exists(settings_path):
        # Create a backup
        copyfile(settings_path, settings_path + ".backup")
    else:
        # Ensure directory exists
        settings_dir = os.path.dirname(settings_path)
        os.makedirs(settings_dir, exist_ok=True)

    with open(settings_path, 'w') as f:
        settings.write(f)


def get_user_config(user: User) -> ConfigParserWithEnv:
    user_settings = UserSettings.find_by_user(user)
    if user_settings is not None:
        user_config = ConfigParserWithEnv(defaults=settings, allow_no_value=True)
        user_config.read_dict({
            'user': user_settings.to_dict()
        })
        return user_config

    return settings
