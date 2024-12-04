import os
import shutil

from django.conf import settings
from django.views.static import directory_index

from ..models import Auction, PhotoSet

IMAGES_EXTENSIONS = [".jpg", ".JPG", ".jpeg", ".JPEG", ".png", ".PNG", ".bmp", ".BMP", ".webp", ".WEBP"]

def get_thumbnail_url(path, base_path):
    # return url to thumbnail of the image
    # replace double backslashes with single backslashes
    # replace backslashes with forward slashes
    url = "http://172.27.70.154/thumbnails/"
    path = path.replace(base_path, '').replace("\\\\", '/').replace("\\", '/')
    return f"{url}{path}"


def list_directory_contents(path=None):
    base_path = os.environ.get("AUCTION_MEDIA_ROOT", settings.MEDIA_ROOT)
    print(base_path)
    if path is not None:
        # Ensure that the path is safe and within the base path
        full_path = os.path.normpath(os.path.join(base_path, path))
        print(full_path)
        if not full_path.startswith(base_path):
            raise ValueError("Attempted to access a path outside of the base path")
    else:
        full_path = base_path

    double_backslash = '\\\\'
    try:
        with os.scandir(full_path) as it:
            entries = [
                {
                    "name": entry.name,
                    "isDir": entry.is_dir(),
                    "id": entry.name,
                    # generate thumbnail url if the entry is a file and has an image extension and replace
                    "thumbnailUrl": get_thumbnail_url(entry.path, base_path) if entry.is_file() and entry.name.endswith(tuple(IMAGES_EXTENSIONS)) else None,
                }
                for entry in it
            ]
        return entries
    except FileNotFoundError:
        raise FileNotFoundError("The specified path does not exist")


def create_directory(path):
    base_path = os.environ.get("AUCTION_MEDIA_ROOT", settings.MEDIA_ROOT)
    full_path = os.path.normpath(os.path.join(base_path, path))
    if not full_path.startswith(base_path):
        raise ValueError("Attempted to create a directory outside of the base path")
    os.makedirs(full_path, exist_ok=True)
    return full_path


def delete_directory(path, recursive=False):
    base_path = os.environ.get("AUCTION_MEDIA_ROOT", settings.MEDIA_ROOT)
    full_path = os.path.normpath(os.path.join(base_path, path))
    if not full_path.startswith(base_path):
        raise ValueError("Attempted to delete a directory outside of the base path")
    if recursive:
        os.removedirs(full_path)
    else:
        os.rmdir(full_path)
    return full_path


def move_files(file_paths, destination_dir, rename_map=None):
    """
    Move files to a specified directory with an optional renaming feature.

    :param file_paths: List of paths of files to move.
    :param destination_dir: The directory to which the files should be moved.
    :param rename_map: Optional dictionary to rename files.
                       Key is the original file name, value is the new name.
    :return: Dictionary containing the original file paths as keys and
             their new paths as values.
    """
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)  # Create destination directory if it doesn't exist

    moved_files = {}
    for file_path in file_paths:
        if not os.path.isfile(file_path):
            print(f"Skipping: {file_path} (Not a valid file)")
            continue

        file_name = os.path.basename(file_path)
        new_name = rename_map.get(file_name, file_name) if rename_map else file_name
        new_path = os.path.join(destination_dir, new_name)

        try:
            shutil.move(file_path, new_path)
            moved_files[file_path] = new_path
            print(f"Moved: {file_path} -> {new_path}")
        except Exception as e:
            print(f"Error moving {file_path} to {new_path}: {e}")

    return moved_files

def put_files_in_completed_directory(auction):
    """
    Move main image and other images to the completed directory.

    :param auction: Auction object.
    :return: Dictionary containing the original file paths as keys and
             their new paths as values.
    """
    auction_name = auction.name

    photoset: PhotoSet = auction.photoset

    directory_location = photoset.directory_location
    main_image = photoset.thumbnail.name
    other_images = photoset.photos.all()
    # completed directory is a directory WYSTAWIONE located in the same directory as the main image currently
    completed_dir = os.path.join(settings.MEDIA_ROOT, directory_location, "WYSTAWIONE")
    rename_map = {os.path.basename(main_image): f"{os.path.basename(main_image)} {auction_name}.jpg"}

    all_files = list(map(lambda x: os.path.join(settings.MEDIA_ROOT, directory_location, x.name), other_images))

    moved_files = move_files(all_files, completed_dir, rename_map)

    # Update the paths in the database
    auction.photoset.directory_location = completed_dir

    # Save the changes
    auction.photoset.save()

    return moved_files
