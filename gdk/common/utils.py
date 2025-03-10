import logging
import shutil
from pathlib import Path

import gdk


def get_static_file_path(file_name):
    """
    Returns the path of the file assuming that is in static directory.

    Parameters
    ----------
        file_name(string): Name of the file in static folder.

    Returns
    -------
        file_path(Path): Returns absolute path of the file if it exists. Else None
    """
    gdk_module_dir = Path(gdk.__file__).resolve().parent
    file_path = gdk_module_dir.joinpath("static").joinpath(file_name).resolve()

    if file_exists(file_path):
        return file_path
    return None


def file_exists(file_path):
    """
    Checks if the given path exists and is a file.

    Parameters
    ----------
        file_path(Path): File path to check.

    Returns
    -------
        (bool): True if the file exists. False if the given path doesn't exist or is not a file.
    """
    logging.debug("Checking if the file '{}' exists.".format(file_path.resolve()))
    # Compatible with < py 3.8
    try:
        return Path(file_path).resolve().is_file()
    except Exception as e:
        logging.debug(e)
        return False


def dir_exists(dir_path):
    """
    Checks if the given path exists and is a directory.

    Parameters
    ----------
        dir_path(Path): File path to check.

    Returns
    -------
        (bool): True if the directory exists. False if the given path doesn't exist or is not a directory.
    """
    logging.debug("Checking if the directory '{}' exists.".format(dir_path.resolve()))
    dp = Path(dir_path).resolve()
    # Compatible with < py 3.8
    try:
        return dp.is_dir()
    except Exception as e:
        logging.debug(e)
        return False


def is_directory_empty(directory_path):
    """
    Checks if the given directory path is empty.

    Parameters
    ----------
        directory_path(Path): Directory path to check.

    Returns
    -------
        (bool): True if the directory exists and is empty. False if directory doesn't exist or not empty.
    """
    dir_path = Path(directory_path).resolve()
    logging.debug("Checking if the directory '{}' exists and is empty.".format(dir_path.resolve()))
    if dir_path.is_dir() and not list(dir_path.iterdir()):
        return True
    return False


def clean_dir(dir):
    """
    Deletes the directory.

    Parameters
    ----------
        dir(Path): Path of the directory to remove.

    Returns
    -------
        None
    """
    logging.debug("Deleting the directory '{}' if it exists.".format(dir.resolve()))
    shutil.rmtree(dir, ignore_errors=True, onerror=None)


error_line = "\n=============================== ERROR ===============================\n"
help_line = "\n=============================== HELP ===============================\n"
current_directory = Path(".").resolve()
log_format = "[%(asctime)s] %(levelname)s - %(message)s"
doc_link_device_role = "https://docs.aws.amazon.com/greengrass/v2/developerguide/device-service-role.html"
