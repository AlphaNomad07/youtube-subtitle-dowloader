import os
import shutil
from fastapi import FastAPI, HTTPException
import yt_dlp
import re

app = FastAPI(
    title="YouTube Subtitles Cleaner",
    description="This API allows you to download and clean subtitles from a YouTube video.",
    version="1.0.0",
)

def clean_subtitles(subtitles: str) -> str:
    """
    Cleans the subtitle text by removing header lines, HTML tags, timestamps, and unwanted characters.
    """
    # Remove WebVTT header lines
    lines = subtitles.splitlines()
    if lines:
        if lines[0].startswith('WEBVTT'):
            lines.pop(0)  # Remove 'WEBVTT' line
        if lines and lines[0].startswith('Kind:'):
            lines.pop(0)  # Remove 'Kind:' line
        if lines and lines[0].startswith('Language:'):
            lines.pop(0)  # Remove 'Language:' line

    # Join lines back into a single string
    clean_text = '\n'.join(lines)

    # Remove timestamps and HTML-like tags
    clean_text = re.sub(r'<[^>]+>', '', clean_text)  # Remove HTML-like tags
    clean_text = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}', '', clean_text)  # Remove timestamps
    clean_text = re.sub(r'align:start position:[^%]+%', '', clean_text)  # Remove alignment and position
    clean_text = re.sub(r'\s+', ' ', clean_text)  # Replace multiple whitespace/newlines with a single space
    clean_text = clean_text.strip()  # Remove leading and trailing whitespace

    return clean_text

def cleanup_files(output_path: str):
    """
    Removes the output directory and its contents.
    """
    if os.path.exists(output_path):
        shutil.rmtree(output_path)

def download_audio_and_subtitles(youtube_url: str, output_path: str = '/tmp/audio') -> dict:
    """
    Downloads subtitles from a YouTube video and returns cleaned subtitles.
    """
    # Ensure the output directory exists
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # Define yt-dlp options for downloading subtitles
    ydl_opts = {
        'format': 'bestaudio/best',  # Download best available audio
        'outtmpl': os.path.join(output_path, 'file.%(ext)s'),  # Output template
        'noplaylist': True,  # Download only the single video, not playlists
        'subtitleslangs': ['en'],  # Download English subtitles (change as needed)
        'writeautomaticsub': True,  # Write automatic subtitles if available
        'subtitlesformat': 'vtt',  # Save subtitles in WebVTT format
        'postprocessors': [],  # No postprocessing
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        },
    }

    try:
        # Create yt-dlp object and download subtitles
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(youtube_url, download=True)
            # Extract subtitle file path
            subtitle_file_path = os.path.join(output_path, 'file.en.vtt')

            # Check if the subtitle file exists and process its content
            if os.path.isfile(subtitle_file_path):
                # Read and clean subtitles into one paragraph
                with open(subtitle_file_path, 'r', encoding='utf-8') as f:
                    subtitles = f.read()

                # Clean the subtitle text
                clean_text = clean_subtitles(subtitles)
                
                # Return JSON object with cleaned subtitles only
                return {
                    'subtitles': clean_text
                }

            else:
                raise HTTPException(status_code=404, detail="No subtitles found for this video.")
    
    except yt_dlp.DownloadError:
        raise HTTPException(status_code=400, detail="Failed to download video or subtitles.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

@app.get("/download/", 
         summary="Download and clean subtitles from a YouTube video",
         description="This endpoint downloads subtitles from the given YouTube video URL, cleans the subtitle text by removing initial WebVTT header lines, timestamps, and unwanted characters, and returns the cleaned subtitles.",
         response_description="The response contains the cleaned subtitles.",
         response_model=dict)
async def download(url: str):
    """
    Downloads and cleans subtitles for a given YouTube URL.

    - **url**: The URL of the YouTube video to download.

    Returns:
        - `subtitles`: The cleaned subtitle text.
    """
    output_path = '/tmp/audio'
    try:
        result = download_audio_and_subtitles(url, output_path)
        return result
    except HTTPException as e:
        raise e
    finally:
        # Cleanup files after processing
        cleanup_files(output_path)
