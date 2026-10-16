import os
import sys
import shutil
import subprocess

SHAREPOINT_FOLDER = r"\\bosch.com\dfsRB\DfsVN\LOC\Hc\RBVH\ETA\05_ETA2\04_CAP-SST\10_Development\999_MemberFolder\TranDuyTuong\AutomationTool\FBL_Billing_Tool"
_SHAREPOINT_VERSION_FILE = os.path.join(SHAREPOINT_FOLDER, "version.info")
_SHAREPOINT_EXE_FILE = os.path.join(SHAREPOINT_FOLDER, "FBLBilling.exe")


def _parse_version(path):
    """Parse TOOL_VERSION value from a version.info file."""
    try:
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith("TOOL_VERSION"):
                    _, _, value = line.partition('=')
                    return value.strip().strip('"').strip("'")
    except Exception:
        pass
    return None


def check_and_update():
    """Check SharePoint for a newer version and auto-update if one is found.

    - If SharePoint files are missing: prints a notice and continues.
    - If already up to date: continues silently.
    - If a new version is found: copies the new exe, launches a batch updater,
      and exits so the updater can replace and restart the exe.
    """
    # If restarted after a successful update, show completion message and continue
    if len(sys.argv) >= 3 and sys.argv[1] == '--updated':
        print(f"Completed update to new version: {sys.argv[2]}")
        return

    from utils.constant import TOOL_VERSION

    current_version = TOOL_VERSION
    print(f"Checking for updates... (current version: {current_version})")

    # Check that both required files exist on SharePoint
    if not os.path.exists(_SHAREPOINT_VERSION_FILE) or not os.path.exists(_SHAREPOINT_EXE_FILE):
        print("No new version update available.")
        return

    sharepoint_version = _parse_version(_SHAREPOINT_VERSION_FILE)
    if sharepoint_version is None:
        print("No new version update available.")
        return

    # Already on the latest version
    if current_version == sharepoint_version:
        print(f"You are using the latest version: {current_version}")
        return

    # A new version is available
    print(f"New version available: {sharepoint_version} (current: {current_version})")
    print("Downloading update... Please wait.")

    # Auto-replacement only works when running as a frozen executable
    if not getattr(sys, 'frozen', False):
        print("(Auto-update is only supported in executable mode. Skipping.)")
        return

    current_exe = sys.executable          # e.g. C:\...\FBL_ReleaseTool.exe
    new_exe_temp = current_exe + ".new"   # temporary download location

    try:
        shutil.copy2(_SHAREPOINT_EXE_FILE, new_exe_temp)
    except Exception as e:
        print(f"Update failed: could not copy new version ({e}). Continuing with current version.")
        return

    # Write a batch script that waits for this process to exit, swaps the exe,
    # starts the new version, then deletes itself.
    batch_file = current_exe + ".update.bat"
    batch_content = (
        "@echo off\n"
        "timeout /t 2 /nobreak >nul\n"
        f'move /y "{new_exe_temp}" "{current_exe}"\n'
        f'start "" "{current_exe}" --updated "{sharepoint_version}"\n'
        'del "%~f0"\n'
    )

    try:
        with open(batch_file, 'w') as f:
            f.write(batch_content)
        subprocess.Popen(
            ['cmd', '/c', batch_file],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
        )
    except Exception as e:
        print(f"Update failed: could not launch updater ({e}). Continuing with current version.")
        try:
            os.remove(new_exe_temp)
        except Exception:
            pass
        return

    print("Update applied. The tool will restart automatically.")
    sys.exit(0)
