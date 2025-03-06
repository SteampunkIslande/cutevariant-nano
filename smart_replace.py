import json
import sys

# Example usage: You'd like to edit all literals that are passed to the translate method of the app object.

# ast-grep --json -p 'self.app.translate("$LIT")' > translate_literals.json
# python smart_replace.py translate_literals.json

# This script will show you every occurrence of every ast-grep meta variable in each file, and prompt you to replace it with a new value.
# If you don't want to replace it, just press enter.

if __name__ == "__main__":
    with open(sys.argv[1], "r", encoding="utf-8") as json_file:
        matches = json.load(json_file)
        file_names = set(m["file"] for m in matches)
        matches_per_file = {
            f: [m for m in matches if m["file"] == f] for f in file_names
        }

        for file_path, matches in matches_per_file.items():
            with open(file_path, "rb") as input_file:
                data = input_file.read()
            byte_offset_offset = 0
            for match in matches:
                for metavar_type in match["metaVariables"]:
                    for metavar_name in match["metaVariables"][metavar_type]:
                        metavar = match["metaVariables"][metavar_type][metavar_name]
                        print("\033c")
                        print(metavar["text"])
                        byteoffset_start = (
                            metavar["range"]["byteOffset"]["start"] + byte_offset_offset
                        )
                        byteoffset_end = (
                            metavar["range"]["byteOffset"]["end"] + byte_offset_offset
                        )
                        replace_with = input("Replace with: ").rstrip().encode("utf-8")
                        if not replace_with:
                            replace_with = metavar["text"].encode("utf-8")
                        data = (
                            data[:byteoffset_start]
                            + replace_with
                            + data[byteoffset_end:]
                        )

                        byte_offset_offset += len(replace_with) - len(
                            metavar["text"].encode("utf-8")
                        )

                with open(file_path, "wb") as f:
                    f.write(data)
