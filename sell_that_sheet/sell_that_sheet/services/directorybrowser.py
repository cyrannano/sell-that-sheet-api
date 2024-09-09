import os
from django.conf import settings


def list_directory_contents(path=None):
    base_path = os.environ.get("AUCTION_MEDIA_ROOT", settings.MEDIA_ROOT)
    if path is not None:
        # Ensure that the path is safe and within the base path
        full_path = os.path.normpath(os.path.join(base_path, path))
        if not full_path.startswith(base_path):
            raise ValueError("Attempted to access a path outside of the base path")
    else:
        full_path = base_path

    try:
        with os.scandir(full_path) as it:
            entries = [
                {"name": entry.name, "isDir": entry.is_dir(), "id": entry.name}
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
