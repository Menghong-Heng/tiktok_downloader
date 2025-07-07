from io import BytesIO
import httpx
import re
import json
import urllib.parse
from typing import Optional, Tuple, List
import tempfile
import subprocess
import yt_dlp
import asyncio

async def resolve_redirect(url: str) -> str:
    """Resolve TikTok redirects to get the final URL"""
    async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
        try:
            r = await client.get(url)
            return str(r.url)
        except Exception:
            return url

async def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from TikTok URL"""
    patterns = [
        r'/video/(\d+)',
        r'/v/(\d+)',
        r'video/(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def get_video_dimensions(input_bytes: bytes) -> tuple:
    """Return (width, height) of video using ffprobe."""
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=True) as in_file:
        in_file.write(input_bytes)
        in_file.flush()
        cmd = [
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'json', in_file.name
        ]
        try:
            result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            info = json.loads(result.stdout)
            width = info['streams'][0]['width']
            height = info['streams'][0]['height']
            return width, height
        except Exception as e:
            print(f"ffprobe failed: {e}")
            return None, None

def check_h264_codec(file_path: str) -> bool:
    """Return True if the video stream in file_path is H.264, else False."""
    cmd = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=codec_name',
        '-of', 'default=noprint_wrappers=1:nokey=1', file_path
    ]
    try:
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        codec = result.stdout.decode().strip()
        return codec == 'h264'
    except Exception as e:
        print(f"ffprobe codec check failed: {e}")
        return False

def convert_to_standard_mp4(input_bytes: bytes) -> bytes:
    """
    Convert video bytes to standard MP4 (H.264/AAC) using ffmpeg.
    - For portrait: crop to 9:16 (centered), scale to 720x1280, setsar=1
    - For landscape: crop to 16:9 (centered), scale to 1280x720, setsar=1
    This matches Stack Overflow best practices for Telegram/iOS display.
    """
    width, height = get_video_dimensions(input_bytes)
    if width is None or height is None:
        # fallback: treat as portrait
        portrait = True
    else:
        portrait = height >= width
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=True) as in_file, \
         tempfile.NamedTemporaryFile(suffix='.mp4', delete=True) as out_file:
        in_file.write(input_bytes)
        in_file.flush()
        if portrait:
            # Portrait: crop to 9:16, scale to 720x1280, setsar=1
            vf = "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=720:1280,setsar=1"
        else:
            # Landscape: crop to 16:9, scale to 1280x720, setsar=1
            vf = "crop=iw:iw*9/16:0:(ih-iw*9/16)/2,scale=1280:720,setsar=1"
        cmd = [
            'ffmpeg',
            '-analyzeduration', '2147483647',
            '-probesize', '2147483647',
            '-y', '-i', in_file.name,
            '-vf', vf,
            '-c:v', 'libx264', '-profile:v', 'baseline', '-level', '3.1', '-crf', '23', '-preset', 'fast', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '128k', '-ar', '44100',
            '-movflags', '+faststart',
            '-map_metadata', '-1',
            '-metadata:s:v', 'rotate=0',
            '-threads', '1',
            '-maxrate', '2M', '-bufsize', '4M',
            out_file.name
        ]
        try:
            result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Post-process: check codec
            codec_info = None
            if not check_h264_codec(out_file.name):
                print("WARNING: Output video is not H.264! Telegram/iOS compatibility may be affected.")
                # Print codec info for debugging
                codec_cmd = [
                    'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                    '-show_entries', 'stream=codec_name',
                    '-of', 'default=noprint_wrappers=1:nokey=1', out_file.name
                ]
                try:
                    codec_result = subprocess.run(codec_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    codec_info = codec_result.stdout.decode().strip()
                    print(f"DEBUG: Output video codec: {codec_info}")
                except Exception as ce:
                    print(f"DEBUG: Could not get codec info: {ce}")
            else:
                print("DEBUG: Output video is H.264 as expected.")
            out_file.seek(0)
            return out_file.read()
        except subprocess.CalledProcessError as e:
            print(f"ffmpeg conversion failed: {e}")
            print(f"ffmpeg stderr: {e.stderr.decode() if e.stderr else 'No stderr output.'}")
            return input_bytes
        except Exception as e:
            print(f"ffmpeg conversion failed (unexpected error): {e}")
            return input_bytes
async def tikwm_api_request(tiktok_url: str) -> Optional[dict]:
    """Helper to call TikWM API and return parsed JSON or None."""
    service_url = "https://tikwm.com/api/"
    data = {
        'url': tiktok_url,
        'hd': '1'
    }
    service_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://tikwm.com',
        'Referer': 'https://tikwm.com/',
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(service_url, data=data, headers=service_headers)
        print(f"TikWM API response: {response.status_code}")
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('code') == 0:
                    return data
            except json.JSONDecodeError:
                print("Failed to parse TikWM JSON response")
    return None

async def fetch_video(tiktok_url: str) -> Tuple[Optional[BytesIO], Optional[str]]:
    """Fetch TikTok video using yt-dlp and re-encode to H.264 for Telegram/iOS compatibility."""
    try:
        # Use yt-dlp + ffmpeg pipeline
        print(f"[yt-dlp] Downloading and re-encoding: {tiktok_url}")
        video_bytes = await async_download_and_reencode_to_h264(tiktok_url)
        if video_bytes:
            buffer = BytesIO(video_bytes)
            caption = f"Downloaded via yt-dlp (H.264 re-encoded) - TikTok Video"
            return buffer, caption
        else:
            print("❌ yt-dlp/ffmpeg pipeline failed")
            return None, None
    except Exception as e:
        print(f"⚠️ Download error: {e}")
        return None, None

async def fetch_photos(tiktok_url: str) -> Tuple[Optional[List[BytesIO]], Optional[str]]:
    """Fetch TikTok photo post images using TikWM API"""
    try:
        # Resolve redirects
        resolved_url = await resolve_redirect(tiktok_url)
        print(f"Resolved URL: {resolved_url}")

        tikwm_data = await tikwm_api_request(tiktok_url)
        if tikwm_data:
            images = tikwm_data.get('data', {}).get('images')
            if images and isinstance(images, list):
                buffers = []
                async with httpx.AsyncClient(timeout=30) as client:
                    for img_url in images:
                        img_resp = await client.get(img_url)
                        if img_resp.status_code == 200:
                            buffers.append(BytesIO(img_resp.content))
                if buffers:
                    caption = f"Downloaded TikTok Photo Post - {tikwm_data.get('data', {}).get('title', 'TikTok Photos')}"
                    return buffers, caption
        return None, None
    except Exception as e:
        print(f"⚠️ Photo download error: {e}")
        return None, None

def download_and_reencode_to_h264(url: str) -> bytes:
    """
    Download video using yt-dlp and re-encode to H.264 using ffmpeg.
    Returns the video as bytes (H.264 MP4).
    """
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=True) as temp_in, \
         tempfile.NamedTemporaryFile(suffix='.mp4', delete=True) as temp_out:
        ydl_opts = {
            'outtmpl': temp_in.name,
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Re-encode to H.264 using ffmpeg
        cmd = [
            'ffmpeg', '-y', '-i', temp_in.name,
            '-c:v', 'libx264', '-crf', '23', '-preset', 'fast',
            '-c:a', 'aac', '-b:a', '128k',
            '-movflags', '+faststart',
            temp_out.name
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        temp_out.seek(0)
        return temp_out.read()

async def async_download_and_reencode_to_h264(url: str) -> bytes:
    """
    Async wrapper for download_and_reencode_to_h264.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, download_and_reencode_to_h264, url)
