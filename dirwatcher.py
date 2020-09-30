from os import walk, listdir
from pathlib import Path


def count_files(directory):
    """"Given a directory it will proceed to count
        all files in it's sub folders. Outputs a dict with sub folder name as key
        and the total file count of that sub folder as value"""
    results = {}
    for sub_dir in listdir(directory):
        full_dir_path = Path(directory, sub_dir)

        all_files = []
        for path, dirs, files in walk(full_dir_path):
            all_files += files

        print(full_dir_path, len(all_files))
        results.update(
            {full_dir_path: len(all_files)}
        )
    return results


if __name__ == "__main__":
    count_files(directory="/srv/sto3/onlyfans/")
