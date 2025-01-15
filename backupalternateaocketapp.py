from flask import Flask, render_template, request, url_for, redirect, send_file, jsonify, send_from_directory
import shutil
import os
from werkzeug.utils import secure_filename
from makingthumbnails import convert_heic_to_jpg, generate_thumbnails
from flask_socketio import SocketIO, send, emit

app = Flask(__name__)
socketio = SocketIO(app)

def request_files(file):
    socketio.emit('upload_file_pls', {"action": "fetch", "file": file}, namespace='/imagestorage')
    return {"status": "Request sent"}, 200

@app.route("/", methods=["POST", "GET"])
def home():
    filenames = []
    try:
        for filename in os.listdir('thumbnails/'):
            filenames.append(filename)
        return render_template("index.html", filenames=filenames)
    except FileNotFoundError:
        return "F Drive is not connected"
    
@app.route("/upload", methods=["POST", "GET"])
def upload():
    if request.method == "POST":
        files = request.files.getlist('fileUpload')
        print(files, "Files uploaded")
        for f in files:
            new_name = secure_filename(f.filename)
            if not os.path.exists(f"photos/{new_name}"):
                f.save(f"preprocessingimages/{new_name}")
        generate_thumbnails(f"preprocessingimages/")
        for file in os.listdir("preprocessingimages/"):
            src = f"preprocessingimages/{file}"
            dst = f"photos/{file}"
            shutil.move(src, dst)
        return redirect(url_for("home"))
    else:
        return render_template("upload.html")

@app.route("/gettingthumbnail/<path:filename>")
def get_thumbnail(filename):
    return send_from_directory('thumbnails/', filename)

@app.route("/loadmedia/<path:filename>")
def load_media(filename):
    return render_template("display.html", filename=filename)

@app.route("/gettingimage/<path:filename>")
def get_image(filename):
    request_files(filename)
    if filename.endswith('.HEIC'):
        if not os.path.exists((f"tempheic/{filename}".replace(".HEIC", "") + ".jpeg")):
            convert_heic_to_jpg(f"photos/{filename}", (f"tempheic/{filename}".replace(".HEIC", "") + ".jpeg"))
        return send_from_directory('tempheic/', (f"{filename}".replace(".HEIC", "") + ".jpeg"))
    return send_from_directory('photos/', filename)

@app.route("/loading/<path:filename>")
def loadingscreen(filename):
    return render_template("loadingscreen.html", filename=filename)

@socketio.on('file_uploaded_boss', namespace='/imagestorage')
def load_loadmediapage():
    socketio.emit('file_loaded')

if __name__ == "__main__":
    app.run(debug=True)