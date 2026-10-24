"""
Script to execute research_model.ipynb cell-by-cell in a persistent kernel session,
capturing real execution outputs and updating research_model.ipynb.
"""

import sys
import os
import io
import json
import time
import base64
import traceback
from contextlib import redirect_stdout, redirect_stderr

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def run_all_cells(notebook_path="research_model.ipynb"):
    print("=" * 80)
    print("EXECUTING NOTEBOOK STEP-BY-STEP:", notebook_path)
    print("=" * 80)

    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # Initialize shared execution namespace (simulating IPython kernel)
    import IPython.display
    from IPython.display import Image as IPImage

    captured_displays = []

    def custom_display(*args, **kwargs):
        for item in args:
            img_path = getattr(item, "filename", None)
            if img_path and os.path.exists(img_path):
                with open(img_path, "rb") as img_f:
                    b64_str = base64.b64encode(img_f.read()).decode("utf-8")
                captured_displays.append({
                    "output_type": "display_data",
                    "data": {
                        "image/png": b64_str,
                        "text/plain": [f"<Figure: {os.path.basename(img_path)}>\n"]
                    },
                    "metadata": {}
                })
            elif hasattr(item, "data") and item.data:
                b64_str = base64.b64encode(item.data).decode("utf-8") if isinstance(item.data, bytes) else str(item.data)
                captured_displays.append({
                    "output_type": "display_data",
                    "data": {
                        "image/png": b64_str,
                        "text/plain": ["<Figure: DisplayData>\n"]
                    },
                    "metadata": {}
                })

    # Patch IPython display module so imported display inside cells uses custom_display
    IPython.display.display = custom_display

    kernel_globals = {
        "__name__": "__main__",
        "__file__": os.path.abspath(notebook_path),
        "display": custom_display,
        "Image": IPImage
    }

    execution_counter = 1
    code_cell_index = 0
    total_code_cells = sum(1 for c in nb["cells"] if c["cell_type"] == "code")

    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] == "markdown":
            first_line = cell["source"][0].strip() if cell["source"] else ""
            if first_line.startswith("#"):
                print(f"\n[SECTION] {first_line}")
            continue

        if cell["cell_type"] == "code":
            code_cell_index += 1
            code_text = "".join(cell["source"])
            first_comment = [l.strip() for l in code_text.splitlines() if l.strip().startswith("#")]
            step_label = first_comment[0] if first_comment else f"Cell {i}"

            print(f"\n>>> Running [{code_cell_index}/{total_code_cells}] {step_label} ...")
            start_t = time.time()

            stdout_buf = io.StringIO()
            stderr_buf = io.StringIO()
            captured_displays.clear()

            cell_outputs = []
            exec_failed = False

            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                try:
                    exec(code_text, kernel_globals)
                except Exception as e:
                    exec_failed = True
                    tb_str = traceback.format_exc()
                    stderr_buf.write(tb_str)

            elapsed = time.time() - start_t
            out_str = stdout_buf.getvalue()
            err_str = stderr_buf.getvalue()

            if out_str:
                cell_outputs.append({
                    "name": "stdout",
                    "output_type": "stream",
                    "text": [line + "\n" for line in out_str.splitlines()]
                })
                # Print a clean snippet of output
                preview_lines = out_str.strip().splitlines()
                if len(preview_lines) <= 6:
                    print("    Output:\n      " + "\n      ".join(preview_lines))
                else:
                    print("    Output:\n      " + "\n      ".join(preview_lines[:3]) + "\n      ... (" + str(len(preview_lines)-4) + " more lines) ...\n      " + preview_lines[-1])

            if err_str:
                cell_outputs.append({
                    "name": "stderr",
                    "output_type": "stream",
                    "text": [line + "\n" for line in err_str.splitlines()]
                })
                print(f"    [STDERR]: {err_str[:200]}")

            if captured_displays:
                cell_outputs.extend(captured_displays)
                print(f"    [DISPLAY]: Captured {len(captured_displays)} visualization charts.")

            cell["outputs"] = cell_outputs
            cell["execution_count"] = execution_counter
            execution_counter += 1

            if exec_failed:
                print(f"❌ [FAILED] Cell {code_cell_index} failed in {elapsed:.2f}s!")
                sys.exit(1)
            else:
                print(f"✅ [OK] Completed in {elapsed:.2f}s")

    # Save updated notebook
    with open(notebook_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)

    print("\n" + "=" * 80)
    print(f"ALL {total_code_cells} CELLS EXECUTED SUCCESSFULLY AND SAVED TO {notebook_path}")
    print("=" * 80)

if __name__ == "__main__":
    run_all_cells()
