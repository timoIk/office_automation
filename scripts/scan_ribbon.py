"""Scan the ribbon/menu bar of Infoniqa to find Neu button."""
from pywinauto import Desktop

desktop = Desktop(backend="uia")
infoniqa = desktop.window(class_name="CamMainFrame")

# Scan ribbon
ribbon = infoniqa.child_window(class_name="{ribbon}", found_index=0)
print("=== Ribbon ===")

def print_tree(ctrl, depth=0, max_depth=3):
    if depth > max_depth:
        return
    try:
        indent = "  " * depth
        name = ctrl.window_text() or "(no text)"
        if len(name) > 80:
            name = name[:80] + "..."
        cls = ctrl.element_info.class_name
        ctrl_type = ctrl.element_info.control_type
        auto_id = ctrl.element_info.automation_id or ""
        print(f"{indent}[{ctrl_type}] {name!r}  class={cls}  id={auto_id!r}")
    except Exception as e:
        print(f"{'  ' * depth}Error: {e}")
        return

    try:
        children = ctrl.children()
        for child in children:
            print_tree(child, depth + 1, max_depth)
    except Exception:
        pass

print_tree(ribbon, 0, 3)

# Also scan the menu bar
print("\n\n=== Menu Bar ===")
menubar = infoniqa.child_window(auto_id="MenuBar")
print_tree(menubar, 0, 2)
