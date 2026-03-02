"""Bring Infoniqa to foreground and take screenshot."""
import time
from pywinauto import Desktop

desktop = Desktop(backend="uia")
infoniqa = desktop.window(class_name="CamMainFrame")
infoniqa.set_focus()
time.sleep(1)

import pyautogui
screenshot = pyautogui.screenshot()
screenshot.save("scripts/infoniqa_invoice_focused.png")
print("Screenshot saved.")
