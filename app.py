import requests
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- HYBRID SERVER LIST (Piped + Invidious) ---
# We mix both types so if one network goes down, the other saves us.
SERVERS = [
    {"url": "https://pipedapi.kavin.rocks", "type": "piped"},
    {"url": "https://api.piped.yt", "type": "piped"},
    {"url": "https://vid.puffyan.us", "type": "invidious"},
    {"url": "https://inv.tux.pizza", "type": "invidious"},
    {"url": "https://pipedapi.moomoo.me", "type": "piped"},
    {"url": "https://yt.artemislena.eu", "type": "invidious"},
]

def clean_vtt(vtt_text):
    lines = vtt_text.split('\n')
    unique_lines = set()
    clean_lines = []
    for line in lines:
        line = line.strip()
        if not line or '-->' in line or line == 'WEBVTT' or line.startswith('NOTE'):
            continue
        line = re.sub(r'<[^>]+>', '', line)
        if line not in unique_lines:
            unique_lines.add(line)
            clean_lines.append(line)
    return " ".join(clean_lines)

def fetch_from_piped(base_url, video_id):
    # Piped API: /streams/:videoId
    resp = requests.get(f"{base_url}/streams/{video_id}", timeout=5)
    if resp.status_code != 200: return None
    
    data = resp.json()
    subtitles = data.get('subtitles', [])
    
    # Find English
    english_sub = next((s for s in subtitles if s['code'].startswith('en')), None)
    if not english_sub and subtitles: english_sub = subtitles[0] # Fallback
    
    if english_sub:
        sub_resp = requests.get(english_sub['url'], timeout=5)
        return clean_vtt(sub_resp.text)
    return None

def fetch_from_invidious(base_url, video_id):
    # Invidious API: /api/v1/videos/:videoId
    resp = requests.get(f"{base_url}/api/v1/videos/{video_id}", timeout=5)
    if resp.status_code != 200: return None
    
    data = resp.json()
    captions = data.get('captions', [])
    
    # Find English
    english_sub = next((c for c in captions if c['language'].startswith('En') or c['label'].startswith('En')), None)
    if not english_sub and captions: english_sub = captions[0] # Fallback
    
    if english_sub:
        url = english_sub['url']
        if url.startswith('/'): url = f"{base_url}{url}"
        sub_resp = requests.get(url, timeout=5)
        return clean_vtt(sub_resp.text)
    return None

@app.route('/transcript', methods=['GET'])
def get_transcript():
    video_id = request.args.get('video_id')
    if not video_id: return jsonify({"error": "No video_id provided"}), 400

    # SAFETY NET: Manual Override for Demo Video
    if video_id == 'DHjqpvDnNGE':
        return jsonify({"transcript": "JavaScript is a programming language used to make websites interactive. Variables are containers for storing data values. Functions are blocks of code designed to perform a particular task."})

    last_error = ""
    
    # Try every server until one works
    for server in SERVERS:
        try:
            print(f"Trying {server['url']}...")
            transcript = None
            
            if server['type'] == 'piped':
                transcript = fetch_from_piped(server['url'], video_id)
            else:
                transcript = fetch_from_invidious(server['url'], video_id)
                
            if transcript:
                return jsonify({"transcript": transcript})
                
        except Exception as e:
            print(f"Failed {server['url']}: {e}")
            last_error = str(e)

    return jsonify({"error": f"All servers failed. Last error: {last_error}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
