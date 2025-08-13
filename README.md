````
______  __________________________       ______                     
___   |/  /__  ____/_  ____/__    |_____ ___  /_____  _____________ 
__  /|_/ /__  __/  _  / __ __  /| |  __ `/_  __ \  / / /_  ___/  _ \
_  /  / / _  /___  / /_/ / _  ___ / /_/ /_  /_/ / /_/ /_(__  )/  __/
/_/  /_/  /_____/  \____/  /_/  |_\__,_/ /_.___/\__,_/ /____/ \___/ 
````
This program automates the creation of multiple MEGA accounts and distributes uploaded files across them.
It is designed for bulk uploading of similar file types and skips JSON files by default.
Folder hierarchy is not preserved—files from subfolders are all uploaded to the MEGA root directory.
Tested primarily with pictures, videos, PDFs, and zip files, it may not work well with complex folder structures (e.g., .git directories).

If you have ideas for new features, want to address any of these limitations, or wish to contribute from the todo list, pull requests are always welcome!

## Install instructions
### Ubuntu (20.04.2)
```bash
git clone git@github.com:11philip22/MEGAabuse.git
sudo apt update
sudo apt install libpcrecpp0v5
sudo ln -s /usr/lib/x86_64-linux-gnu/libpcre.so.3 /usr/lib/x86_64-linux-gnu/libpcre.so.1
chmod +x MEGAabuse/binaries/megacmd_linux/*
chmod +x MEGAabuse/binaries/megatools_linux/*
chmod +x MEGAabuse/MEGAabuse.py
```

```bash
sudo apt install libc-ares-dev libcrypto++6 libfreeimage3
cd MEGAabuse/megaabuse/mega/
sudo cp libmega.so /usr/local/lib/
sudo ldconfig
```

### Arch
```bash
sudo pacman -S c-ares libraw crypto++ libsodium freeimage
git clone git@github.com:11philip22/MEGAabuse.git
chmod +x MEGAabuse/binaries/megacmd_linux/*
chmod +x MEGAabuse/binaries/megatools_linux/*
chmod +x MEGAabuse/MEGAabuse.py
cd MEGAabuse/megaabuse/mega/
sudo cp libmega.so /usr/local/lib/
sudo ldconfig
```

## Usage
``./MEGAabuse.py -h``  
``./MEGAabuse.py -d <path to folder i want to upload>``  
``./MEGAabuse.py -d <path to folder i want to upload> <second path> <more paths>``

## Acknowledgements
- https://github.com/ncjones/python-guerrillamail
