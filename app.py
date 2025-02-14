from flask import Flask, render_template, request, url_for, redirect, send_file, jsonify, send_from_directory, session
import shutil
import os
from werkzeug.utils import secure_filename
from makingthumbnails import convert_heic_to_jpg
from flask_socketio import SocketIO
import zipfile
import uuid
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
socketio = SocketIO(app)

clients = {}

def get_drive_files(file, md):
    socketio.call('drive_files', {"action": "fetch", "file": file, "socket_index":md.socket_index}, namespace='/imagestorage', to=list(clients.keys())[0])
    return {"status": "Request sent"}, 200

def post_drive_files(file, md):
    socketio.call('drive_files', {"action":"download", "file":file, "socket_index":md.socket_index}, namespace='/imagestorage', to=list(clients.keys())[0])
    return {"status": "Request sent"}, 200

def get_thumbnails(md):
    socketio.call('get_thumbnails_from_drive', {"socket_index":md.socket_index}, namespace='/imagestorage', to=list(clients.keys())[0])
    return {"status": "Request sent"}, 200

class MyDirectiories:
    def __init__(self, session_id, socket_index):
        self.session_id = session_id
        self.socket_index = socket_index
        self.PHOTOS = f"photos_{session_id}"
        self.TEMPHEIC = f"tempheic_{session_id}"
        self.TODRIVE = f"photosToDrive_{session_id}"
        self.THUMBNAILS = f"thumbnails_{session_id}"

    def arg_dict(self):
        return {"session_id": self.session_id, "socket_index":self.socket_index}

def setUpSession():
    session_id = str(uuid.uuid4())
    session['session_id'] = session_id
    session_clients_index = len(clients.get(list(clients.keys())[0]))
    print(clients[list(clients.keys())[0]])
    clients[list(clients.keys())[0]].append(session_id)
    md = MyDirectiories(session_id=session_id, socket_index=session_clients_index)
    session['session_directories'] = md.arg_dict()
    os.mkdir(md.PHOTOS)
    os.mkdir(md.TEMPHEIC)
    os.mkdir(md.TODRIVE)

@app.route("/testing")
def testingRoute():
    return f"{clients.get(list(clients.keys())[0])}"

@app.route("/", methods=["POST", "GET"])
def home():
    # filenames = []
    if not session.get('session_id'):
        setUpSession()
    return redirect(url_for('testingRoute'))
    try:
        print(session['session_directories'])
        # https://www.geeksforgeeks.org/what-does-the-double-star-operator-mean-in-python/
        # pertaining to function arguments
        md = MyDirectiories(**session['session_directories'])
        if not os.path.exists(md.THUMBNAILS):
            get_thumbnails(md)
        # for filename in os.listdir('thumbnails/'):
        #     filenames.append(filename)
        return render_template("index.html", filenames=os.listdir(md.THUMBNAILS))
    except Exception as e:
        return f"F Drive is not connected, {e}"
    
@app.route("/upload", methods=["POST", "GET"])
def upload():
    print(session.get('session_id'))
    md = MyDirectiories(**session['session_directories'])
    if request.method == "POST":
        files = request.files.getlist('files')
        print(files, "Files uploaded")
        for f in files:
            new_name = secure_filename(f.filename)
            f.save(f"{md.TODRIVE}/{new_name}")
            f.save(f"{md.PHOTOS}/{new_name}")
        shutil.make_archive(md.TODRIVE, 'zip', md.TODRIVE)
        post_drive_files(f"{md.TODRIVE}.zip")
        if os.path.exists(md.TODRIVE):
            shutil.rmtree(md.TODRIVE)  # Delete the folder and its contents
            os.remove(f"{md.TODRIVE}.zip")
        os.makedirs(md.TODRIVE)
        return redirect(url_for("home"))
    else:
        return render_template("upload.html")

@app.route("/gettingthumbnail/<path:filename>")
def get_thumbnail(filename):
    md = MyDirectiories(**session['session_directories'])
    return send_from_directory(md.THUMBNAILS, filename)

@app.route("/loadmedia/<path:filename>")
def load_media(filename):
    md = MyDirectiories(**session['session_directories'])
    if not os.path.exists(f"{md.PHOTOS}/{filename}"):
        get_drive_files(filename)
    return render_template("display.html", filename=filename)

@app.route("/gettingimage/<path:filename>")
def get_image(filename):
    md = MyDirectiories(**session['session_directories'])
    if filename.endswith('.HEIC'):
        temp_heic_file_dir = f"{md.TEMPHEIC}/{filename}".replace(".HEIC", "") + ".jpeg"
        if not os.path.exists(temp_heic_file_dir):
            convert_heic_to_jpg(f"{md.PHOTOS}/{filename}", temp_heic_file_dir)
        return send_from_directory(md.TEMPHEIC, (f"{filename}".replace(".HEIC", "") + ".jpeg"))
    return send_from_directory(f'{md.PHOTOS}/', filename)

# FUNCTIONS AND ENDPOINTS PERTAINING THE DRIVE CLIENT
# THESE WILL NOT WORK WITH CURRENT SESSION IMPLEMENTATION SINCE IT IS A DIFFERENT CLIENT THEREFORE DIFFERENT SESSION

@app.route("/upload_from_imagestorage_client", methods=["POST"])
def imagestorageupload():
    md = MyDirectiories(**session['session_directories'])
    file = request.files['file']
    new_name = secure_filename(file.filename)
    file.save(f"{md.PHOTOS}/{new_name}")
    return {"status": "Request received"}, 200

@app.route("/download_from_imagestorage_client", methods=["GET"])
def imagestoragedownload():
    md = MyDirectiories(**session['session_directories'])
    return send_from_directory('.', f"{md.TODRIVE}.zip")

@app.route("/upload_thumbnails_from_imagestorage_client", methods=["POST"])
def thumbnailstorageupload():
    data = request.form.get('socket_index')
    file = request.files['file']
    print(clients.get(list(clients.keys())[0]))
    session_id = clients.get(list(clients.keys())[0])[int(data)]
    md = MyDirectiories(session_id=session_id, socket_index=None)
    new_name = f"{md.THUMBNAILS}.zip"
    file.save(f"{new_name}")
    with zipfile.ZipFile(new_name, 'r') as zip_ref:
        zip_ref.extractall(md.THUMBNAILS)
    return {"status": "Request received"}, 200

@app.route("/upload_new_thumbnails_from_imagestorage_client", methods=["POST"])
def newlyaddedthumbnailstorageupload():
    md = MyDirectiories(**session['session_directories'])
    files = request.files.getlist('files')
    for file in files:
        new_name = secure_filename(file.filename)
        if not os.path.exists(f"{md.THUMBNAILS}/{new_name}"):
            file.save(f"{md.THUMBNAILS}/{new_name}")
    return {"status": "Request received"}, 200

@socketio.on('connect', namespace='/imagestorage')
def handle_connect():
    print("Client connected: ", request.sid)
    clients[request.sid] = []

@socketio.on('disconnect', namespace='/imagestorage')
def handle_disconnect():
    print("Client disconnected")

if __name__ == "__main__":
    socketio.run(app, port=8081, host="0.0.0.0", debug=True)

# TODO: Change timeout for the socket call