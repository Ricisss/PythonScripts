import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from OneDrive import uploadFile

def WatchPath(folder_path, APP_ID):
    class NewFileHandler(FileSystemEventHandler):
        def on_created(self, event):
            if not event.is_directory:
                filename = event.src_path
                name = os.path.basename(filename)
                path = os.path.dirname(filename)
                uploadFile(path, name, APP_ID)

    def process_new_file(filename):
        # Do whatever you need to do with the new file here
        print(f"Processing new file: {filename}")


    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(event_handler, path=folder_path, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    def my_callback(filename):
        process_new_file(filename)
        # Call any other functions you need to process the new file here

    watch_folder_for_new_files('/path/to/watched/folder/', my_callback)
