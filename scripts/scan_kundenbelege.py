"""Scan the Kundenbelege window in Infoniqa in detail."""
from pywinauto import Desktop

desktop = Desktop(backend="uia")
infoniqa = desktop.window(class_name="CamMainFrame")
arbeitsbereich = infoniqa.child_window(class_name="MDIClient")
kundenbelege = arbeitsbereich.child_window(title="Kundenbelege", class_name="CamDialog")

print(f"=== {kundenbelege.window_text()} ===\n")

def print_tree(ctrl, depth=0, max_depth=4):
    if depth > max_depth:
        return
    try:
        indent = "  " * depth
        name = ctrl.window_text() or "(no text)"
        # Truncate long names
        if len(name) > 60:
            name = name[:60] + "..."
        cls = ctrl.element_info.class_name
        ctrl_type = ctrl.element_info.control_type
        auto_id = ctrl.element_info.automation_id or ""
        enabled = ctrl.is_enabled()
        print(f"{indent}[{ctrl_type}] {name!r}  class={cls}  id={auto_id!r}  enabled={enabled}")
    except Exception as e:
        print(f"{'  ' * depth}Error: {e}")
        return

    try:
        children = ctrl.children()
        for child in children:
            print_tree(child, depth + 1, max_depth)
    except Exception:
        pass

print_tree(kundenbelege, 0, 4)
