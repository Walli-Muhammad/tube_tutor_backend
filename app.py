import os
import time
import glob
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import yt_dlp

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------
# CONFIGURE GEMINI
# ---------------------------------------------------------
GENAI_API_KEY = "AIzaSyDQ-WmcF1G52Zpcj99zQEDAKPjDrf_OvEI"
genai.configure(api_key=GENAI_API_KEY)

# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------
def download_audio(video_url):
    """Downloads the audio of the video (faster than full video) using yt-dlp."""
    timestamp = int(time.time())
    filename = f"audio_{timestamp}"
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': filename,
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        # yt-dlp adds the extension, so we find the file
        files = glob.glob(f"{filename}.*")
        return files[0] if files else None
    except Exception as e:
        print(f"Download Error: {e}")
        return None

@app.route('/generate_app', methods=['POST'])
def generate_app():
    data = request.json
    video_url = data.get('video_url')
    
    if not video_url:
        return jsonify({"error": "No video_url provided"}), 400

    print(f"Processing: {video_url}")
    audio_path = None
    
    try:
        # 1. DOWNLOAD (Use yt-dlp to get the content)
        print("Downloading audio...")
        audio_path = download_audio(video_url)
        if not audio_path:
            return jsonify({"error": "Failed to download video content"}), 500

        # 2. UPLOAD TO GEMINI
        print("Uploading to Gemini...")
        # Uploading the file to Google's temporary storage
        video_file = genai.upload_file(path=audio_path)
        
        # Wait for processing (usually instant for audio)
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai.get_file(video_file.name)

        if video_file.state.name == "FAILED":
            return jsonify({"error": "Gemini failed to process the file"}), 500

        # 3. GENERATE CONTENT
        print("Generating App...")
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")
        
        prompt = """
        You are an expert developer. The user has provided a video/audio file.
        Based strictly on the content of this file, create a single-file HTML5 educational app.
        
        Requirements:
        1. Return ONLY raw HTML code. Do not use markdown (```).
        2. The app must be interactive (Quiz, Guide, or Flashcards).
        3. Extract the key lessons from the audio.
        """
        
        response = model.generate_content([video_file, prompt])
        
        # 4. CLEANUP (Delete file from Google and Local server)
        genai.delete_file(video_file.name)
        os.remove(audio_path)

        return jsonify({"html": response.text})

    except Exception as e:
        print(f"Error: {e}")
        # Cleanup if crash
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Ensure ffmpeg is installed on the server environment
    app.run(host='0.0.0.0', port=10000)
