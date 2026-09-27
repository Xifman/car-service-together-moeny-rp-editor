import json
import os
import shutil
from pathlib import Path
from datetime import datetime

GAME_SAVE_ROOT = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "AppData" / "LocalLow" / "V12 Studio" / "CarServiceTogether" / "Saves" / "Main"

RP_KEYS = [
    "reputationPoints",
    "reputation",
    "rp",
    "RP",
]

MONEY_KEYS = [
    "money",
    "cash",
    "balance",
    "currency",
    "Money",
    "Cash",
]

def find_key_recursive(obj, wanted_keys, path=""):
    results = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key

            if key in wanted_keys and isinstance(value, (int, float)):
                results.append((current_path, key, value))

            results.extend(find_key_recursive(value, wanted_keys, current_path))

    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            current_path = f"{path}[{i}]"
            results.extend(find_key_recursive(value, wanted_keys, current_path))

    return results

def set_by_path(data, target_path, new_value):
    parts = []
    current = ""
    i = 0

    while i < len(target_path):
        if target_path[i] == ".":
            if current:
                parts.append(current)
                current = ""
            i += 1
        elif target_path[i] == "[":
            if current:
                parts.append(current)
                current = ""
            end = target_path.index("]", i)
            parts.append(int(target_path[i + 1:end]))
            i = end + 1
        else:
            current += target_path[i]
            i += 1

    if current:
        parts.append(current)

    obj = data
    for part in parts[:-1]:
        obj = obj[part]

    obj[parts[-1]] = new_value

def load_json(path):
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)

def save_json(path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def format_time(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

def main():
    print("=" * 58)
    print(" Car Service Together - Save Money / RP Editor")
    print("=" * 58)

    if not GAME_SAVE_ROOT.exists():
        print("\nSave folder was not found:")
        print(GAME_SAVE_ROOT)
        print("\nStart the game and create/save a game first.")
        input("\nPress Enter to exit...")
        return

    files = []
    for p in GAME_SAVE_ROOT.rglob("*.json"):
        try:
            data = load_json(p)
            money = find_key_recursive(data, MONEY_KEYS)
            rp = find_key_recursive(data, RP_KEYS)

            # Only show JSON files that look like actual saves.
            if money or rp:
                files.append((p, data, money, rp))
        except Exception:
            pass

    if not files:
        print("\nNo editable JSON saves containing money/RP were found.")
        print("Save root:", GAME_SAVE_ROOT)
        input("\nPress Enter to exit...")
        return

    files.sort(key=lambda item: item[0].stat().st_mtime, reverse=True)

    print("\nFound saves:\n")
    for index, (path, data, money, rp) in enumerate(files, 1):
        money_text = ", ".join(f"{v} ({p})" for p, _, v in money) if money else "not found"
        rp_text = ", ".join(f"{v} ({p})" for p, _, v in rp) if rp else "not found"

        print(f"[{index}] {path.name}")
        print(f"    Folder:   {path.parent.name}")
        print(f"    Modified: {format_time(path.stat().st_mtime)}")
        print(f"    Money:    {money_text}")
        print(f"    RP:       {rp_text}")
        print()

    while True:
        try:
            choice = int(input(f"Pick save [1-{len(files)}]: "))
            if 1 <= choice <= len(files):
                break
        except ValueError:
            pass
        print("Invalid choice.")

    save_path, data, money_matches, rp_matches = files[choice - 1]

    print("\nSelected:")
    print(save_path)

    while True:
        print("\nWhat do you want to change?")
        print("[1] Money")
        print("[2] RP")
        print("[3] Both")
        print("[0] Exit")
        action = input("> ").strip()

        if action in {"0", "1", "2", "3"}:
            break

    if action == "0":
        return

    changes = []

    def choose_match(matches, label):
        if not matches:
            print(f"\nCould not find {label} automatically.")
            return None

        if len(matches) == 1:
            return matches[0]

        print(f"\nMultiple possible {label} values found:")
        for i, (path, key, value) in enumerate(matches, 1):
            print(f"[{i}] {value}  ->  {path}")

        while True:
            try:
                c = int(input("Pick the correct one: "))
                if 1 <= c <= len(matches):
                    return matches[c - 1]
            except ValueError:
                pass
            print("Invalid choice.")

    if action in {"1", "3"}:
        match = choose_match(money_matches, "money")
        if match:
            path, key, old = match
            while True:
                try:
                    new = int(input(f"New money (current {old}): ").replace(",", "").replace(" ", ""))
                    break
                except ValueError:
                    print("Enter a whole number.")
            changes.append(("Money", path, old, new))

    if action in {"2", "3"}:
        match = choose_match(rp_matches, "RP")
        if match:
            path, key, old = match
            while True:
                try:
                    new = int(input(f"New RP (current {old}): ").replace(",", "").replace(" ", ""))
                    break
                except ValueError:
                    print("Enter a whole number.")
            changes.append(("RP", path, old, new))

    if not changes:
        print("\nNothing to change.")
        input("\nPress Enter to exit...")
        return

    print("\nChanges:")
    for label, path, old, new in changes:
        print(f"  {label}: {old} -> {new}")

    confirm = input("\nApply changes? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = save_path.with_suffix(save_path.suffix + f".backup_{timestamp}")
    shutil.copy2(save_path, backup_path)

    for label, target_path, old, new in changes:
        set_by_path(data, target_path, new)

    save_json(save_path, data)

    print("\nDone.")
    print("Edited:", save_path)
    print("Backup:", backup_path)
    print("\nIf Steam Cloud restores the old save, close the game and Steam before editing,")
    print("or temporarily disable Steam Cloud for the game.")

    input("\nPress Enter to exit...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
    except Exception as e:
        print("\nERROR:", e)
        input("\nPress Enter to exit...")
