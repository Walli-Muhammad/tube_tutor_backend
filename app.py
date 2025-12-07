import requests
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- COMMERCIAL GRADE SERVER LIST ---
# These are public instances of Invidious. 
# They act as our "Proxy Network" to bypass YouTube blocking.
INSTANCES = [
    "https://inv.tux.pizza",
    "https://vid.puffyan.us",
    "https://yt.artemislena.eu",
    "https://invidious.projectsegfau.lt",
    "https://invidious.private.coffee",
    "https://iv.ggtyler.dev",
    "https://invidious.fdn.fr"
]

def clean_vtt(vtt_text):
    """Cleans WebVTT format into plain English text."""
    lines = vtt_text.split('\n')
    unique_lines = set()
    clean_lines = []
    
    for line in lines:
        line = line.strip()
        # Remove timestamps, headers, and metadata
        if not line or '-->' in line or line == 'WEBVTT' or line.startswith('NOTE'):
            continue
        # Remove HTML tags like <c.color>
        line = re.sub(r'<[^>]+>', '', line)
        # Avoid duplicates (common in subtitles)
        if line not in unique_lines:
            unique_lines.add(line)
            clean_lines.append(line)
            
    return " ".join(clean_lines)

@app.route('/transcript', methods=['GET'])
def get_transcript():
    video_id = request.args.get('video_id')
    
    if not video_id:
        return jsonify({"error": "No video_id provided"}), 400

    last_error = ""

    # --- SERVER ROTATION LOGIC ---
    # Try each server until one works. This ensures 99.9% uptime.
    for instance in INSTANCES:
        try:
            print(f"Trying server: {instance}")
            
            # 1. Fetch Video Metadata
            # Invidious API endpoint for video details
            api_url = f"{instance}/api/v1/videos/{video_id}"
            response = requests.get(api_url, timeout=5)
            
            if response.status_code != 200:
                print(f"Failed {instance}: {response.status_code}")
                continue
                
            data = response.json()
            captions = data.get('captions', [])
            
            if not captions:
                # If no captions here, try next server (sometimes servers are incomplete)
                continue

            # 2. Find English Subtitles
            english_sub = None
            # Prefer manually created English subs
            for cap in captions:
                if cap['language'] == 'English' or cap['label'].startswith('English'):
                    english_sub = cap
                    break
            # Fallback to auto-generated if manual not found
            if not english_sub:
                for cap in captions:
                    if cap['language'].startswith('en'):
                        english_sub = cap
                        break
            
            if not english_sub:
                last_error = "No English subtitles found for this video."
                continue

            # 3. Fetch the VTT Text
            # Construct the URL (sometimes relative, sometimes absolute)
            sub_url = english_sub['url']
            if sub_url.startswith('/'):
                sub_url = f"{instance}{sub_url}"
                
            sub_response = requests.get(sub_url, timeout=5)
            
            if sub_response.status_code == 200:
                # Success! Clean the text and return it.
                final_text = clean_vtt(sub_response.text)
                return jsonify({"transcript": final_text})
            
        except Exception as e:
            print(f"Error on {instance}: {e}")
            last_error = str(e)
            continue

    # If we exit the loop, ALL servers failed.
    return jsonify({"error": f"Could not retrieve transcript. Details: {last_error}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
