import os
import base64
from PIL import Image
import ffmpeg
import pyheif

def convert_heic_to_jpg(heic_path, output_path):
    try:
        heif_file = pyheif.read(heic_path)
        image = Image.frombytes(
            heif_file.mode, 
            heif_file.size, 
            heif_file.data,
            "raw",
            heif_file.mode,
            heif_file.stride,
        )
        image.save(output_path, "JPEG")
    except ValueError as e:
        if "Input is not a HEIF/AVIF file" in str(e):
            # Rename mislabeled HEIC to JPG
            new_path = heic_path.replace(".HEIC", ".jpeg")
            os.rename(heic_path, new_path)
            print(f"Renamed mislabeled HEIC to JPEG: {new_path}")
        else:
            print(f"Unexpected error with file {heic_path}: {e}")
    except Exception as e:
        print(f"An error occurred while processing {heic_path}: {e}")

def create_thumbnail_image(image_path, proper_name=None, proper_ext=None):
    with Image.open(image_path) as img:
        if img.mode == "P" and image_path.lower().endswith('gif'):
            img = img.convert("RGB")
        img.thumbnail((200, 200))  # Resize to thumbnail size
        name_without_ext, ext = os.path.splitext(os.path.basename(image_path))
        ext_without_dot = ext.lstrip(".")
        if not proper_ext:
            img.save(f"thumbnails/{name_without_ext}_{ext_without_dot}_thumbnail.jpeg", format='JPEG')
        else:
            img.save(f"thumbnails/{proper_name}_{proper_ext}_thumbnail.jpeg", format='JPEG')

def create_thumbnail_video(video_path):
    name_without_ext, ext = os.path.splitext(os.path.basename(video_path))
    ext_without_dot = ext.lstrip(".")
    thumbnail_path = f"thumbnails/{name_without_ext}_{ext_without_dot}_frame.jpg"
    ffmpeg.input(video_path, ss=1).output(thumbnail_path, vframes=1).run(overwrite_output=True)
    create_thumbnail_image(thumbnail_path, name_without_ext, ext_without_dot)
    os.remove(thumbnail_path)

def generate_thumbnails(folder_path):
    print(os.listdir(folder_path))
    for file in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file)
        print(file_path)
        if file.endswith('HEIC'):
            convert_heic_to_jpg(file_path, (file_path.replace(".HEIC", "") + ".jpeg"))
            name_without_ext, ext = os.path.splitext(os.path.basename(file_path))
            ext_without_dot = ext.lstrip(".")
            create_thumbnail_image(file_path.replace(".HEIC", "") + ".jpeg", name_without_ext, ext_without_dot)
            os.remove(file_path.replace(".HEIC", "") + ".jpeg")
        elif file.lower().endswith(('png', 'jpg', 'jpeg', 'gif')):
            create_thumbnail_image(file_path)
        elif file.lower().endswith(('mp4', 'mov', 'avi')):
            create_thumbnail_video(file_path)

# folder_path = "photos/"
# generate_thumbnails(folder_path)
