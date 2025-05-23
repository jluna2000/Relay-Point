from flask import Flask, render_template, request, url_for, redirect, send_file, jsonify, send_from_directory
import shutil
import os
from werkzeug.utils import secure_filename
from makingthumbnails import convert_heic_to_jpg
from flask_socketio import SocketIO
import zipfile
import uuid
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
socketio = SocketIO(app)
if not os.path.exists('photos'):
    os.mkdir('photos')
    os.mkdir('tempheic')
    os.mkdir('photosToDrive')
    os.mkdir('photosToDriveArcs')

clients = []
currently_uploading = {}

def popZip(zip_file):
    if zip_file:
        if currently_uploading.get(zip_file):
            currently_uploading.pop(zip_file)
        if os.path.exists(f'photosToDriveArcs/{zip_file}'):
            os.remove(f'photosToDriveArcs/{zip_file}')

def get_drive_files(file):
    socketio.call('drive_files', {"action": "fetch", "file": file}, namespace='/imagestorage', to=clients[0])
    return {"status": "Request sent"}, 200

def post_drive_files(file):
    socketio.emit('drive_files', {"action":"download", "file":file}, namespace='/imagestorage', callback=popZip, to=clients[0])
    return {"status": "Request sent"}, 200

def get_thumbnails():
    socketio.call('get_thumbnails_from_drive', namespace='/imagestorage', to=clients[0])
    return {"status": "Request sent"}, 200

@app.route("/", methods=["POST", "GET"])
def home():
    try:
        if not os.path.exists(f"thumbnails"):
            get_thumbnails()
        return render_template("index.html", filenames=os.listdir('thumbnails/'))
    except FileNotFoundError:
        return "F Drive is not connected"
    
@app.route("/upload", methods=["POST", "GET"])
def upload():
    if request.method == "POST":
        files = request.files.getlist('files')
        print(files, "Files uploaded")
        for f in files:
            new_name = secure_filename(f.filename)
            f.save(f"photosToDrive/{new_name}")
            shutil.copy(f"photosToDrive/{new_name}", f"photos/{new_name}")
        new_archive = secure_filename(f"arc_{datetime.now()}.zip")
        new_arc_nozip = new_archive.replace('.zip', '')
        shutil.make_archive(new_arc_nozip, 'zip', "photosToDrive")
        shutil.move(new_archive, f"photosToDriveArcs/{new_archive}")
        currently_uploading[new_archive] = os.listdir('photosToDrive')
        post_drive_files(new_archive)
        if os.path.exists("photosToDrive"):
            shutil.rmtree("photosToDrive")  # Delete the folder and its contents
        os.makedirs("photosToDrive")
        return redirect(url_for("home"))
    else:
        return render_template("upload.html")

@app.route("/gettingthumbnail/<path:filename>")
def get_thumbnail(filename):
    return send_from_directory('thumbnails/', filename)

@app.route("/loadmedia/<path:filename>")
def load_media(filename):
    if not os.path.exists(f"photos/{filename}"):
        get_drive_files(filename)
    return render_template("display.html", filename=filename)

@app.route("/gettingimage/<path:filename>")
def get_image(filename):
    if filename.endswith('.HEIC'):
        if not os.path.exists((f"tempheic")):
            os.mkdir("tempheic")
        if not os.path.exists((f"tempheic/{filename}".replace(".HEIC", "") + ".jpeg")):
            convert_heic_to_jpg(f"photos/{filename}", (f"tempheic/{filename}".replace(".HEIC", "") + ".jpeg"))
        return send_from_directory('tempheic/', (f"{filename}".replace(".HEIC", "") + ".jpeg"))
    return send_from_directory('photos/', filename)

# FUNCTIONS AND ENDPOINTS PERTAINING THE DRIVE CLIENT

@app.route("/upload_from_imagestorage_client", methods=["POST"])
def imagestorageupload():
    file = request.files['file']
    new_name = secure_filename(file.filename)
    file.save(f"photos/{new_name}")
    return {"status": "Request received"}, 200

@app.route("/download_from_imagestorage_client/<filename>", methods=["GET"])
def imagestoragedownload(filename):
    return send_from_directory('photosToDriveArcs', filename)

@app.route("/upload_thumbnails_from_imagestorage_client", methods=["POST"])
def thumbnailstorageupload():
    file = request.files['file']
    new_name = secure_filename(file.filename)
    file.save(f"{new_name}")
    with zipfile.ZipFile(new_name, 'r') as zip_ref:
        zip_ref.extractall('thumbnails')
    return {"status": "Request received"}, 200

@app.route("/upload_new_thumbnails_from_imagestorage_client", methods=["POST"])
def newlyaddedthumbnailstorageupload():
    files = request.files.getlist('files')
    for file in files:
        new_name = secure_filename(file.filename)
        if not os.path.exists(f"thumbnails/{new_name}"):
            file.save(f"thumbnails/{new_name}")
    return {"status": "Request received"}, 200

@socketio.on('connect', namespace='/imagestorage')
def handle_connect():
    print("Client connected: ", request.sid)
    clients.append(request.sid)

@socketio.on('disconnect', namespace='/imagestorage')
def handle_disconnect():
    print("Client disconnected")

if __name__ == "__main__":
    socketio.run(app, port=8081, host="0.0.0.0", debug=True)

# TODO: HANDLE EXCEPTIONS CAUSED BY PILLOW IN FILESERVER