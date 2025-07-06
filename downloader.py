from io import BytesIO
import httpx
import re
import json
import urllib.parse
from typing import Optional, Tuple, List
import tempfile
import subprocess

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

def convert_to_standard_mp4(input_bytes: bytes) -> bytes:
    """Convert video bytes to standard MP4 (H.264/AAC) using ffmpeg, force 9:16 aspect (720x1280) with padding, remove all metadata and rotation info."""
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=True) as in_file, \
         tempfile.NamedTemporaryFile(suffix='.mp4', delete=True) as out_file:
        in_file.write(input_bytes)
        in_file.flush()
        vf = "scale=w=720:h=1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2"
        cmd = [
            'ffmpeg',
            '-analyzeduration', '2147483647',
            '-probesize', '2147483647',
            '-y', '-i', in_file.name,
            '-vf', vf,
            '-c:v', 'libx264', '-preset', 'fast', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '128k',
            '-movflags', '+faststart',
            '-map_metadata', '-1',
            '-metadata:s:v', 'rotate=0',
            '-threads', '1',
            out_file.name
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out_file.seek(0)
            return out_file.read()
        except Exception as e:
            print(f"ffmpeg conversion failed: {e}")
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
    """Fetch TikTok video without watermark - optimized version"""
    try:
        # Resolve redirects
        resolved_url = await resolve_redirect(tiktok_url)
        print(f"Resolved URL: {resolved_url}")
        
        # Extract video ID
        video_id = await extract_video_id(resolved_url)
        if not video_id:
            print("❌ Could not extract video ID")
            return None, None
        
        print(f"Video ID: {video_id}")
        
        # Primary method: TikWM API (POST) - most reliable
        try:
            tikwm_data = await tikwm_api_request(tiktok_url)
            if tikwm_data:
                video_url = tikwm_data.get('data', {}).get('hdplay') or tikwm_data.get('data', {}).get('play')
                if video_url:
                    async with httpx.AsyncClient(timeout=60) as client:
                        video_response = await client.get(video_url)
                        if video_response.status_code == 200:
                            # Convert to standard MP4
                            converted_bytes = convert_to_standard_mp4(video_response.content)
                            buffer = BytesIO(converted_bytes)
                            quality = "HD" if tikwm_data.get('data', {}).get('hdplay') else "Standard"
                            return buffer, f"Downloaded via TikWM ({quality}) - {tikwm_data.get('data', {}).get('title', 'TikTok Video')}"
        except Exception as e:
            print(f"TikWM API failed: {e}")
        
        # Fallback method: Direct TikTok API (if TikWM fails)
        try:
            api_url = f"https://api.tiktokv.com/aweme/v1/play/?video_id={video_id}&vr_type=0&is_play_url=1&source=PackSourceEnum_PUBLISH&media_id={video_id}&ratio=720p&line=0&file_id={video_id}&quality=720p&watermark=0"
            api_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.tiktok.com/',
                'X-Requested-With': 'com.zhiliaoapp.musically',
                'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5',
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(api_url, headers=api_headers)
                print(f"TikTok API fallback response: {response.status_code}")
                
                if response.status_code == 200 and len(response.content) > 1000:
                    # Convert to standard MP4
                    converted_bytes = convert_to_standard_mp4(response.content)
                    buffer = BytesIO(converted_bytes)
                    return buffer, f"Downloaded via TikTok API (ID: {video_id})"
        except Exception as e:
            print(f"TikTok API fallback failed: {e}")
        
        print("❌ All download methods failed")
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
