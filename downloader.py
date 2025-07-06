from io import BytesIO
import httpx
import re
import json
import urllib.parse
from typing import Optional, Tuple, List

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
                            # Try HD first, then fallback to regular
                            video_url = data.get('data', {}).get('hdplay') or data.get('data', {}).get('play')
                            if video_url:
                                video_response = await client.get(video_url, timeout=60)
                                if video_response.status_code == 200:
                                    buffer = BytesIO(video_response.content)
                                    quality = "HD" if data.get('data', {}).get('hdplay') else "Standard"
                                    return buffer, f"Downloaded via TikWM ({quality}) - {data.get('data', {}).get('title', 'TikTok Video')}"
                    except json.JSONDecodeError:
                        print("Failed to parse TikWM JSON response")
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
                    buffer = BytesIO(response.content)
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
                        # Check if it's a photo post
                        images = data.get('data', {}).get('images')
                        if images and isinstance(images, list):
                            buffers = []
                            for img_url in images:
                                img_resp = await client.get(img_url, timeout=30)
                                if img_resp.status_code == 200:
                                    buffers.append(BytesIO(img_resp.content))
                            if buffers:
                                caption = f"Downloaded TikTok Photo Post - {data.get('data', {}).get('title', 'TikTok Photos')}"
                                return buffers, caption
                except json.JSONDecodeError:
                    print("Failed to parse TikWM JSON response for photos")
        return None, None
    except Exception as e:
        print(f"⚠️ Photo download error: {e}")
        return None, None
