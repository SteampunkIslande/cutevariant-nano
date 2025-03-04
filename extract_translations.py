#!/usr/bin/env python

import json
import subprocess

# jq '(.[].metaVariables.single.TO_TRANSLATE.text)'

if __name__ == "__main__":
    p = subprocess.run(
        ["ast-grep", "scan", "--json", "--rule", "extract-translations.yaml"],
        capture_output=True,
        text=True,
    )
    translations = json.loads(p.stdout)
    to_translate_texts = {
        item["metaVariables"]["single"]["TO_TRANSLATE"]["text"] for item in translations
    }
    print(to_translate_texts)
