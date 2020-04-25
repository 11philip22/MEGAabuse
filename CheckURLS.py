from pathlib import Path
from os import path

script_dir = path.dirname(path.realpath(__file__))  # Comment for ipython

exports = []
e_urls = []

output_file = Path(script_dir, "out.txt")
with open(output_file) as outp_file:
    # Dividing outfile into list by blank line
    for file_line in outp_file:
        clean_line = file_line.strip("\n")

        if file_line == "\n":
            exports.append(e_urls)
            e_urls = []
        else:
            e_urls.append(clean_line)

data_dict = {}
for export in exports:
    # First line is folder path. All lines after that export urls
    data_dict.update({export[0]: export[1:]})

for fn, el in data_dict.items():  # Folder path, export list; List containing exported urls
    print(f"Checking health of: {fn}")

    for u in el:
        print(f"Checking {u}")
        # todo: check if url is up
