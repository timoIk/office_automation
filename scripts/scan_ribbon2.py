"""Scan Infoniqa ribbon area and menu items."""
from pywinauto import Desktop

desktop = Desktop(backend="uia")
infoniqa = desktop.window(class_name="CamMainFrame")

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
        for child in ctrl.children():
            print_tree(child, depth + 1, max_depth)
    except Exception:
        pass

# Scan with auto_id 99 (ribbon pane from earlier scan)
print("=== Ribbon Pane (id=99) ===")
ribbon = infoniqa.child_window(auto_id="99")
print_tree(ribbon, 0, 3)

# Main menu bar (first one)
print("\n=== Main Menu (top) ===")
menubar = infoniqa.child_window(auto_id="MenuBar", found_index=0)
print_tree(menubar, 0, 2)
