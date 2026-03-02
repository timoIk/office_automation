"""Scan the new invoice form that just opened in Infoniqa."""
import pyautogui
from pywinauto import Desktop

# Screenshot first
screenshot = pyautogui.screenshot()
screenshot.save("scripts/infoniqa_invoice_form.png")
print("Screenshot saved.\n")

# Scan the form via UIA
desktop = Desktop(backend="uia")
infoniqa = desktop.window(class_name="CamMainFrame")
arbeitsbereich = infoniqa.child_window(class_name="MDIClient")

print("=== MDI Children (open tabs) ===")
for child in arbeitsbereich.children():
    try:
        title = child.window_text()
        cls = child.element_info.class_name
        print(f"  [{cls}] {title!r}")
    except Exception as e:
        print(f"  Error: {e}")

# Find the invoice form (should be a new CamDialog)
print("\n=== Looking for new invoice form ===")
dialogs = arbeitsbereich.children()
for dialog in dialogs:
    title = dialog.window_text()
    if "Home" in title or "Kundenbelege" in title:
        continue
    print(f"\nForm: {title!r}")
    # Scan all controls in this form
    try:
        for d in dialog.descendants():
            try:
                ct = d.element_info.control_type
                name = d.window_text() or "(no text)"
                if len(name) > 80:
                    name = name[:80] + "..."
                cls = d.element_info.class_name
                auto_id = d.element_info.automation_id or ""
                if ct in ("Edit", "Pane", "Text", "ComboBox", "CheckBox", "Button",
                          "DataGrid", "Custom"):
                    rect = d.rectangle()
                    print(f"  [{ct}] {name!r}  class={cls}  id={auto_id!r}  rect={rect}")
            except Exception:
                pass
    except Exception as e:
        print(f"  Error scanning: {e}")
