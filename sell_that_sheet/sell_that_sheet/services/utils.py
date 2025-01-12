import os
import random
import unicodedata
import base64
import shutil
import glob
import logging
from typing import List
import glob
import math
from pprint import pprint
from urllib import parse
from PIL import Image, ImageDraw, ImageFont, ImageFile
import unicodedata
from PIL import Image
from io import BytesIO
import shutil
import os
import base64
from django.conf import settings

ImageFile.LOAD_TRUNCATED_IMAGES = True

def copy_images_convert_to_jpg(dir1, dir2):
    # List of common image file formats
    supported_formats = ['.jpg', '.jpeg', '.png', '.gif', '.webp']

    # Create dir2 if it doesn't exist
    if not os.path.exists(dir2):
        os.makedirs(dir2)

    # Iterate over files in dir1
    for filename in os.listdir(dir1):
        filepath = os.path.join(dir1, filename)

        # Check if file is an image
        if os.path.isfile(filepath) and any(ext in filename.lower() for ext in supported_formats):
            try:
                # Copy the file to dir2
                new_filename = filename.strip()
                new_filepath = os.path.join(dir2, new_filename)
                shutil.copy2(filepath, new_filepath)

                # Change the file extension to .jpg
                new_filename_jpg = os.path.splitext(new_filename)[0] + '.JPG'
                new_filepath_jpg = os.path.join(dir2, new_filename_jpg)
                os.rename(new_filepath, new_filepath_jpg)
                # print(f"Copied and converted: {filename} -> {new_filename_jpg}")
            except Exception as e:
                print(f"Error converting {filename}: {str(e)}")



def limit_photo_size(photos):
    MAX_SIZE_MB = 2
    max_size_bytes = MAX_SIZE_MB * 1024 * 1024  # Convert MB to bytes
    limited_photos = []

    for img in photos:
        defimg = img.copy()
        # set format to jpg
        img_format = 'JPEG'
        img = img.convert('RGB')  # Convert image to RGB format for consistency
        img_bytes = BytesIO()
        img.save(img_bytes, format=img_format)
        img_bytes.seek(0)

        if len(img_bytes.getvalue()) <= max_size_bytes:
            # limited_photos.append(img_bytes.getvalue())
            encoded_string = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
            # save image to text file

            # with open("test.txt", "w") as f:
            #     f.write(encoded_string)

            limited_photos.append("data:"+str(encoded_string))
        else:
            # If the image exceeds the size limit, resize it while maintaining aspect ratio
            img.thumbnail((800, 800))  # Resize to a maximum of 800x800 pixels
            resized_img_bytes = BytesIO()
            # img.save(resized_img_bytes, format=img_format)
            resized_img_bytes.seek(0)
            encoded_string = base64.b64encode(resized_img_bytes.getvalue()).decode('utf-8')
            limited_photos.append("data:"+str(encoded_string))
            # limited_photos.append(str(resized_img_bytes.getvalue()))

    return limited_photos


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def check_if_starter_photo(starters, photo):
    for x in starters:
        # normalize x and photo to NFC form
        x = unicodedata.normalize('NFC', x)
        photo = unicodedata.normalize('NFC', photo)
        if photo.find(x) < 0:
            continue
        else:
            return True
    return False

NUMERRATED_SUFFIX = '_numerated'

def get_photos_names(dir, starters):
    descriptions = starters
    photos = []
    for filename in glob.glob(dir + '/*.JPG') + glob.glob(dir + '/*.JPEG'):
        if(filename.find('_merge') != -1): continue
        if(filename.find(NUMERRATED_SUFFIX) != -1): continue
        filename = filename.replace('\\', '/')
        if('JPEG' in filename):
            photos.append(filename[:-5])
        else:
            photos.append(filename[:-4])
    photos = sorted(photos)
    photo_sets = []
    photo_set = []

    for x in photos:
        if check_if_starter_photo(descriptions, x) and len(photo_set) > 0:
            photo_sets.append(photo_set)
            photo_set = []
            photo_set.append(x)
        else:
            photo_set.append(x)

    if(len(photo_set) > 0): photo_sets.append(photo_set)

    return photo_sets

# NOTE: photos - list of names of photos
def merge_photos(photos):
    # If merge_potos was called for an empty list just return an empty list
    if(len(photos) < 2): return []

    photos = list(chunks(photos, 4))
    merged_name = []

    merged = []


    for phot in photos:
        if(len(phot) == 2):
            img_size = (2048, 1536//2)
            collage = Image.new("RGB", img_size, color=(255,255,255,255))
            c = 0
            for i in range(0, img_size[0], img_size[0]//2):
                photo = phot[c]
                photo = photo.resize((img_size[0]//2,img_size[1]))

                collage.paste(photo, (i,0))
                c += 1
            merged += [collage]
            # filename = phot[0] + "_merge"
            # merged_name += [filename]

            # collage.save(filename + NUMERRATED_SUFFIX + '.JPG')

        else:
            img_size = (2048, 1536)
            collage = Image.new("RGB", img_size, color=(255,255,255,255))
            c = 0
            for i in range(0, img_size[0], img_size[0]//2):
                for j in range(0, img_size[1], img_size[1]//2):
                    photo = phot[c]
                    photo = photo.resize((img_size[0]//2,img_size[1]//2))

                    collage.paste(photo, (i,j))
                    c += 1
                    if(c >= len(phot)): break
                if(c >= len(phot)): break

            # filename = phot[0] + "_merge"
            # merged_name += [filename]
            # collage.save(filename + NUMERRATED_SUFFIX + '.JPG')
            merged += [collage]

    return merged

def add_numeration_on_image(img: Image, num):
    font = ImageFont.truetype(os.path.join(settings.STATIC_ROOT, 'fonts/Roboto-Black.ttf'), 60)
    photo = Image.open(img).convert("RGB")

    offset = 10
    if num != 0:
        draw = ImageDraw.Draw(photo)
        draw.text((0 + offset, 0 + offset),str(num),(255,255,255),font=font, stroke_fill=(0,0,0), stroke_width=2)

    return photo

def parse_photos(image_set, max_photos=12):
    MAX_PHOTOS = max_photos
    PACK_SIZE = 4

    numerated = []
    for i, photo in enumerate(image_set):
        numerated.append(add_numeration_on_image(photo, i))

    reserved = math.ceil((len(image_set) - MAX_PHOTOS) / (PACK_SIZE - 1))
    to_merge = numerated[abs(MAX_PHOTOS - reserved):]

    merged = merge_photos(to_merge)
    photos_list = numerated[:abs(MAX_PHOTOS - reserved)] + merged
    return photos_list

logger = logging.getLogger(__name__)

def prepare_temp_directory(base_dir: str = "./tmp") -> str:
    directory = os.path.join(base_dir, f"tmp_{random.randint(1, 1000000)}")
    if os.path.exists(directory):
        shutil.rmtree(directory)
    os.makedirs(directory)
    return directory

def remove_temp_directory(directory: str):
    shutil.rmtree(directory)
    logger.info(f"Temporary directory {directory} removed")

def copy_files(src_dir: str, dest_dir: str):
    for file in glob.glob(os.path.join(src_dir, '*.xlsx')):
        if '~$' not in file:
            shutil.copy(file, os.path.join(dest_dir, 'aukcje.xlsx'))
    # Add logic to copy images as well, with conversion if needed.
    logger.info(f"Files copied to {dest_dir}")

def normalize_unicode(text: str) -> str:
    return unicodedata.normalize('NFC', text)

# def limit_photo_size(photo_sets: List[str], max_photos: int = 12) -> List[str]:
#     return photo_sets[:max_photos] if len(photo_sets) > max_photos else photo_sets

def get_photo_base64(photo_path: str) -> str:
    with open(photo_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def rotate_image(image_path, degrees):
    """
    Rotate an image clockwise by 90 degrees.

    :param image_path: Path to the image file.
    :return: True if the image was rotated successfully, False otherwise.
    """
    try:
        from PIL import Image
    except ImportError:
        return False

    try:
        with Image.open(image_path) as img:
            img = img.rotate(degrees, expand=True)
            img.save(image_path)
        return True
    except Exception as e:
        print(f"Error rotating image {image_path}: {e}")
        return False


