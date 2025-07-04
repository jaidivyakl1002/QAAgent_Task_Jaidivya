import whisper
import yt_dlp
import os
from typing import Optional, Dict
import logging
from config.settings import settings

class VideoProcessor:
    def __init__(self):
        self.whisper_model = whisper.load_model("base")
        self.logger = logging.getLogger(__name__)
        
    def download_youtube_video(self, url: str, output_path: str) -> Optional[str]:
        """Download YouTube video and return path to audio file"""
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': f'{output_path}/%(title)s.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
            # Find the downloaded file
            for file in os.listdir(output_path):
                if file.endswith('.mp3'):
                    return os.path.join(output_path, file)
                    
        except Exception as e:
            self.logger.error(f"Error downloading video: {e}")
            return None
    
    def transcribe_video(self, video_path: str) -> Optional[Dict]:
        """Transcribe video using Whisper"""
        try:
            result = self.whisper_model.transcribe(video_path)
            return {
                'text': result['text'],
                'segments': result['segments'],
                'language': result['language']
            }
        except Exception as e:
            self.logger.error(f"Error transcribing video: {e}")
            return None
    
    def process_recruter_video(self) -> Optional[Dict]:
        """Process the specific Recruter.ai video"""
        video_url = "https://youtu.be/IK62Rk47aas"
        
        # Download video
        audio_path = self.download_youtube_video(video_url, settings.VIDEOS_DIR)
        if not audio_path:
            return None
            
        # Transcribe
        transcript = self.transcribe_video(audio_path)
        if not transcript:
            return None
            
        # Save transcript
        transcript_path = os.path.join(settings.TRANSCRIPTS_DIR, "recruter_tutorial.json")
        with open(transcript_path, 'w') as f:
            import json
            json.dump(transcript, f, indent=2)
            
        return transcript