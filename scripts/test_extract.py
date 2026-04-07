from pathlib import Path
import pypff

base_folder = Path(__file__).resolve().parent.parent
pst_path = base_folder / "data" / "archive.pst"

print("Trying to open:", pst_path)

pst = pypff.file()
pst.open(str(pst_path))

root = pst.get_root_folder()
print("Root folder:", root.name)

def walk(folder, depth=0):
    indent = "  " * depth
    print(f"{indent}Folder: {folder.name}")

    for i in range(min(folder.number_of_sub_messages, 3)):
        msg = folder.get_sub_message(i)

        subject = msg.subject if msg.subject else "(no subject)"
        sender = msg.sender_name if msg.sender_name else "(unknown sender)"
        body = msg.plain_text_body if msg.plain_text_body else ""

        print(f"{indent}  -----")
        print(f"{indent}  Subject: {subject}")
        print(f"{indent}  Sender: {sender}")
        print(f"{indent}  Body preview: {body[:150]}")

    for j in range(folder.number_of_sub_folders):
        walk(folder.get_sub_folder(j), depth + 1)

walk(root)
pst.close()