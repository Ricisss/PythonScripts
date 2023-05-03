import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from OneDrive import uploadFile

def WatchPath(WATCH_PATH, APP_ID):
    class NewFileHandler(FileSystemEventHandler):
        def on_created(self, event):
            if not event.is_directory:
                file_path = event.src_path
                print(f"New file created: {file_path}")
                process_new_file(file_path)

    def process_new_file(file_path):
        # Do whatever you need to do with the new file here
        print(f"Processing new file: {file_path}")
        uploadFile(file_path, APP_ID)

    if __name__ == "__main__":
        event_handler = NewFileHandler()
        observer = Observer()
        observer.schedule(event_handler, path=WATCH_PATH, recursive=True)
        observer.start()

        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            #observer.stop()
            print("Hupsík dupsík")
        observer.join()
