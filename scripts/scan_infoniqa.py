"""Scan Infoniqa ONE Start main window controls (depth-limited)."""
from pywinauto import Desktop

desktop = Desktop(backend="uia")
infoniqa = desktop.window(class_name="CamMainFrame")

print(f"=== Main Window: {infoniqa.window_text()} ===\n")

# Print control hierarchy (depth 2 to avoid overwhelming output)
def print_tree(ctrl, depth=0, max_depth=2):
    if depth > max_depth:
        return
    try:
        indent = "  " * depth
        name = ctrl.window_text() or "(no text)"
        cls = ctrl.element_info.class_name
        ctrl_type = ctrl.element_info.control_type
        auto_id = ctrl.element_info.automation_id or ""
        rect = ctrl.rectangle()
        print(f"{indent}[{ctrl_type}] {name!r}  class={cls}  auto_id={auto_id!r}  rect={rect}")
    except Exception as e:
        print(f"{'  ' * depth}Error: {e}")
        return

    try:
        children = ctrl.children()
        for child in children:
            print_tree(child, depth + 1, max_depth)
    except Exception:
        pass

print_tree(infoniqa, 0, 2)
