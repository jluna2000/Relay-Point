from flask import Flask, render_template, request, url_for, redirect, send_file, jsonify, send_from_directory
import shutil
import os
from werkzeug.utils import secure_filename
from makingthumbnails import convert_heic_to_jpg, generate_thumbnails
from flask_socketio import SocketIO, send, emit

app = Flask(__name__)
socketio = SocketIO(app)

clients = []

def request_files(file):
    socketio.call('my_message', {"action": "fetch", "file": file}, namespace='/imagestorage', to=clients[0])
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

@app.route("/upload_from_imagestorage_client", methods=["POST"])
def imagestorageupload():
    file = request.files['file']
    new_name = secure_filename(file.filename)
    if not os.path.exists(f"photos/{new_name}"):
        file.save(f"photos/{new_name}")
    return {"status": "Request received"}, 200

@socketio.on('connect', namespace='/imagestorage')
def handle_connect():
    print("Client connected: ", request.sid)
    clients.append(request.sid)

@socketio.on('disconnect', namespace='/imagestorage')
def handle_disconnect():
    print("Client disconnected")

if __name__ == "__main__":
    socketio.run(app, host="192.168.1.191", port=5000, debug=True)