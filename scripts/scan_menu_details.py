"""Scan menu items in detail - get their positions and try to read tooltips."""
from pywinauto import Desktop, Application

# UIA backend - get menu items with their rectangles
desktop = Desktop(backend="uia")
infoniqa = desktop.window(class_name="CamMainFrame")

print("=== Menu Items (with positions, UIA) ===")
menubar = infoniqa.child_window(auto_id="MenuBar", found_index=1)
for item in menubar.children():
    try:
        rect = item.rectangle()
        name = item.window_text() or "(no text)"
        # Try to get more info
        props = item.get_properties()
        help_text = props.get("help_text", "")
        legacy_name = ""
        try:
            legacy_name = item.legacy_properties().get("Name", "")
        except Exception:
            pass
        print(f"  rect={rect}  text={name!r}  help={help_text!r}  legacy={legacy_name!r}")
    except Exception as e:
        print(f"  Error: {e}")

# Win32 backend - try getting menu
print("\n=== Win32 Menu ===")
try:
    app = Application(backend="win32").connect(class_name="CamMainFrame")
    main = app.window(class_name="CamMainFrame")
    menu = main.menu()
    if menu:
        for item in menu.items():
            print(f"  Menu item: {item.text()!r}  id={item.item_id()}")
except Exception as e:
    print(f"Error getting menu: {e}")

# Check CamExplorerBar (left sidebar - might have navigation)
print("\n=== CamExplorerBar (left sidebar, win32) ===")
try:
    explorer = main.child_window(class_name="{CamExplorerBar}")
    for c in explorer.children():
        try:
            print(f"  class={c.class_name()!r}  text={c.window_text()!r}")
        except Exception as e:
            print(f"  Error: {e}")
except Exception as e:
    print(f"Error: {e}")
