import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

path = 'D:\python'

def WatchPath(WATCH_PATH):
    class NewFileHandler(FileSystemEventHandler):
        def on_created(self, event):
            if not event.is_directory:
                filename = event.src_path
                print(f"New file created: {filename}")
                process_new_file(filename)

    def process_new_file(filename):
        # Do whatever you need to do with the new file here
        print(f"Processing new file: {filename}")

    if __name__ == "__main__":
        event_handler = NewFileHandler()
        observer = Observer()
        observer.schedule(event_handler, path=WATCH_PATH, recursive=True)
        observer.start()

        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

WatchPath(path)
