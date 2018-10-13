from YtManagerApp.models import Video
from YtManagerApp import scheduler
from YtManagerApp.appconfig import get_user_config
import os
import youtube_dl
import logging

log = logging.getLogger('video_downloader')
log_youtube_dl = log.getChild('youtube_dl')


def __build_youtube_dl_params(video: Video, user_config):
    # resolve path
    format_dict = {
        'channel': video.subscription.channel.name,
        'channel_id': video.subscription.channel.channel_id,
        'playlist': video.subscription.name,
        'playlist_id': video.subscription.playlist_id,
        'playlist_index': "{:03d}".format(1 + video.playlist_index),
        'title': video.name,
        'id': video.video_id,
    }

    user_config.set_additional_interpolation_options(**format_dict)

    download_path = user_config.get('user', 'DownloadPath')
    output_pattern = user_config.get('user', 'DownloadFilePattern')
    output_path = os.path.join(download_path, output_pattern)
    output_path = os.path.normpath(output_path)

    youtube_dl_params = {
        'logger': log_youtube_dl,
        'format': user_config.get('user', 'DownloadFormat'),
        'outtmpl': output_path,
        'writethumbnail': True,
        'writedescription': True,
        'writesubtitles': user_config.getboolean('user', 'DownloadSubtitles'),
        'writeautomaticsub': user_config.getboolean('user', 'DownloadAutogeneratedSubtitles'),
        'allsubtitles': user_config.getboolean('user', 'DownloadSubtitlesAll'),
        'postprocessors': [
            {
                'key': 'FFmpegMetadataPP'
            },
        ]
    }

    sub_langs = user_config.get('user', 'DownloadSubtitlesLangs').split(',')
    sub_langs = [i.strip() for i in sub_langs]
    if len(sub_langs) > 0:
        youtube_dl_params['subtitleslangs'] = sub_langs

    sub_format = user_config.get('user', 'DownloadSubtitlesFormat')
    if len(sub_format) > 0:
        youtube_dl_params['subtitlesformat'] = sub_format

    return youtube_dl_params, output_path


def download_video(video: Video, attempt: int = 1):

    log.info('Downloading video %d [%s %s]', video.id, video.video_id, video.name)

    user_config = get_user_config(video.subscription.user)
    max_attempts = user_config.getint('user', 'DownloadMaxAttempts', fallback=3)

    youtube_dl_params, output_path = __build_youtube_dl_params(video, user_config)
    with youtube_dl.YoutubeDL(youtube_dl_params) as yt:
        ret = yt.download(["https://www.youtube.com/watch?v=" + video.video_id])

    log.info('Download finished with code %d', ret)

    if ret == 0:
        video.downloaded_path = output_path
        video.save()
        log.error('Video %d [%s %s] downloaded successfully!', video.id, video.video_id, video.name)

    elif attempt <= max_attempts:
        log.warning('Re-enqueueing video (attempt %d/%d)', attempt, max_attempts)
        scheduler.instance.add_job(download_video, args=[video, attempt + 1])

    else:
        log.error('Multiple attempts to download video %d [%s %s] failed!', video.id, video.video_id, video.name)
        video.downloaded_path = ''
        video.save()


def schedule_download_video(video: Video):
    """
    Schedules a download video job to run immediately.
    :param video:
    :return:
    """
    scheduler.instance.add_job(download_video, args=[video, 1])
