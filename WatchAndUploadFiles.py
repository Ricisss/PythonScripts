import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from OneDrive import uploadFile


def WatchPath(folder_path):
    class NewFileHandler(FileSystemEventHandler):
        def on_moved(self, event):
            if not event.is_directory:
                filename = event.dest_path
                name = os.path.basename(filename)
                path = os.path.dirname(filename)
                extension = os.path.splitext(filename)[1]
                print(f"on_created {filename}")
                if extension == ".jpg" or extension == ".png":
                    uploadFile(path, name)
                else:
                    print(f"wrong extension: {extension}")   

    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(event_handler, path=folder_path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    