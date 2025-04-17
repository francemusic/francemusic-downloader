from flask import Flask, request, render_template, send_file, Response, stream_with_context, jsonify
from flask_cors import CORS
import yt_dlp
import os
import uuid
import time
import logging

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
CORS(app)

progress_data = {"percent": 0.0}

def progress_hook(d):
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '0.0%').strip()
        try:
            progress_data["percent"] = float(percent.replace('%', ''))
        except:
            progress_data["percent"] = 0.0

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/download", methods=["POST"])
def download():
    try:
        url = request.form["url"]
        format = request.form.get("format", "mp3")
        print(f"URL recibida: {url}")
        print(f"Formato recibido: {format}")

        video_id = str(uuid.uuid4())
        output_path = f"downloads/{video_id}.%(ext)s"

        format_map = {
            "mp3": "bestaudio/best",
            "360p": "bestvideo[height<=360]+bestaudio/best",
            "720p": "bestvideo[height<=720]+bestaudio/best",
            "1080p": "bestvideo[height<=1080]+bestaudio/best",
            "1440p": "bestvideo[height<=1440]+bestaudio/best"
        }

        ydl_opts = {
            'format': format_map.get(format, "bestaudio/best"),
            'outtmpl': output_path,
            'progress_hooks': [progress_hook],
            'merge_output_format': 'mp4' if format != 'mp3' else 'mp3'
        }

        if os.path.exists("cookies.txt"):
            ydl_opts['cookiefile'] = "cookies.txt"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        ext = "mp3" if format == "mp3" else "mp4"
        final_file = output_path.replace("%(ext)s", ext)
        if not os.path.exists(final_file):
            files = [f for f in os.listdir("downloads") if video_id in f]
            if files:
                final_file = os.path.join("downloads", files[0])

        if os.path.exists("cookies.txt"):
            os.remove("cookies.txt")

        print(f"Archivo final listo para enviar: {final_file}")
        return jsonify({"file": final_file})

    except Exception as e:
        app.logger.error(f"Error en /download: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route("/fetch", methods=["POST"])
def fetch():
    try:
        data = request.json
        filepath = data.get("file")
        print(f"Petición para fetch del archivo: {filepath}")
        if filepath and os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        return "Archivo no encontrado", 404
    except Exception as e:
        app.logger.error(f"Error en /fetch: {e}")
        return "Error interno en el servidor", 500

@app.route("/progress")
def progress():
    def generate():
        while True:
            yield f"data: {progress_data['percent']}\n\n"
            time.sleep(0.5)
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

if __name__ == "__main__":
    os.makedirs("downloads", exist_ok=True)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), threaded=True)
