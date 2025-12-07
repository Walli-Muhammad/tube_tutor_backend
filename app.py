from flask import Flask, request, jsonify
from flask_cors import CORS
from youtube_transcript_api import YouTubeTranscriptApi

app = Flask(__name__)
CORS(app) # Allow your Flutter app to talk to this

@app.route('/transcript', methods=['GET'])
def get_transcript():
    video_id = request.args.get('video_id')

    if not video_id:
        return jsonify({"error": "No video_id provided"}), 400

    try:
        # 1. Fetch transcript (this runs on the US server, so no blocks!)
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)

        # 2. Combine into a single string
        full_text = " ".join([t['text'] for t in transcript_list])

        return jsonify({"transcript": full_text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)