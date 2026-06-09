"""
Replace audio track in video (for video notes / circles).
Uses ffmpeg — free, local.
"""
import asyncio
import ffmpeg


async def replace_audio_in_video(
    video_path: str,
    new_audio_path: str,
    output_path: str,
) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _replace_sync, video_path, new_audio_path, output_path)


def _replace_sync(video_path: str, new_audio_path: str, output_path: str) -> str:
    video = ffmpeg.input(video_path).video
    audio = ffmpeg.input(new_audio_path).audio

    (
        ffmpeg
        .output(video, audio, output_path, vcodec="copy", acodec="aac", shortest=None)
        .overwrite_output()
        .run(quiet=True)
    )
    return output_path
