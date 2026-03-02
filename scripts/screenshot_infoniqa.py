"""Take a screenshot of the Infoniqa menu area."""
import pyautogui

# Take screenshot of just the top menu area
screenshot = pyautogui.screenshot(region=(0, 0, 1920, 200))
screenshot.save("scripts/infoniqa_menu.png")
print("Screenshot saved to scripts/infoniqa_menu.png")

# Also full window
screenshot_full = pyautogui.screenshot()
screenshot_full.save("scripts/infoniqa_full.png")
print("Full screenshot saved to scripts/infoniqa_full.png")
