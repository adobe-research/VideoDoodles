from pathlib import Path


data_root_folder = str((Path(__file__).resolve().parent.parent / 'raw-data'))
default_backend_data_folder = str((Path(__file__).resolve().parent.parent / 'app' / 'backend' / 'data'))
default_frontend_data_folder = str((Path(__file__).resolve().parent.parent / 'app' / 'frontend' / 'public' / 'data'))
