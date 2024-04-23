from pathlib import Path
import os
import re

# Preprocessed data folder: this is used when reading color frames in test scripts
# It assumes that a folder preprocessed_data with subfolders for each video is available in the following hierarchy wrt to this file:
# <root>
#   raw-data
#       <video-name>
#       ...
#   app
#       backend
#           scripts
#               paths.py
#       frontend
preprocessed_data_folder = str((Path(__file__).resolve().parent.parent.parent.parent / 'raw-data'))

backend_data_root_folder = str((Path(__file__).resolve().parent.parent / 'data'))
keyframe_records_folder = str((Path(__file__).resolve().parent.parent / 'keyframe_records'))
traj_export_folder = str((Path(__file__).resolve().parent.parent / 'exports' / 'trajectory'))
orientations_export_folder = str((Path(__file__).resolve().parent.parent / 'exports' / 'orientations'))


def get_available_videos():

    vids = [f.name for f in os.scandir(backend_data_root_folder) if (f.is_dir() and not re.search("^_.+", f.name))]
    vids.sort()

    return vids
        