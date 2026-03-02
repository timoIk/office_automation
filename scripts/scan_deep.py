"""Deep scan of Infoniqa - try both backends and look for buttons/toolbars."""
from pywinauto import Desktop
import pywinauto

# Try UIA backend - get ALL descendants
desktop = Desktop(backend="uia")
infoniqa = desktop.window(class_name="CamMainFrame")

print("=== All Buttons/MenuItems in Infoniqa (UIA) ===")
try:
    descendants = infoniqa.descendants()
    for d in descendants:
        try:
            ct = d.element_info.control_type
            if ct in ("Button", "MenuItem", "ToolBar", "SplitButton"):
                name = d.window_text() or "(no text)"
                cls = d.element_info.class_name
                auto_id = d.element_info.automation_id or ""
                rect = d.rectangle()
                print(f"  [{ct}] {name!r}  class={cls}  id={auto_id!r}  rect={rect}")
        except Exception:
            pass
except Exception as e:
    print(f"Error: {e}")

# Now try win32 backend
print("\n=== Win32 backend - top level children ===")
try:
    from pywinauto import Application
    app = Application(backend="win32").connect(class_name="CamMainFrame")
    main = app.window(class_name="CamMainFrame")
    # Print toolbar controls
    for ctrl in main.children():
        try:
            cls = ctrl.class_name()
            text = ctrl.window_text() or "(no text)"
            print(f"  class={cls!r}  text={text!r}")
        except Exception as e:
            print(f"  Error: {e}")
except Exception as e:
    print(f"Error: {e}")
