"""Scan all open windows to find Infoniqa ONE Start."""
from pywinauto import Desktop

desktop = Desktop(backend="uia")
windows = desktop.windows()
for w in windows:
    try:
        title = w.window_text()
        cls = w.element_info.class_name
        pid = w.process_id()
        print(f"Title: {title!r}  |  Class: {cls}  |  PID: {pid}")
    except Exception as e:
        print(f"Error: {e}")
