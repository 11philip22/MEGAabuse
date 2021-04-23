````
______  __________________________       ______                     
___   |/  /__  ____/_  ____/__    |_____ ___  /_____  _____________ 
__  /|_/ /__  __/  _  / __ __  /| |  __ `/_  __ \  / / /_  ___/  _ \
_  /  / / _  /___  / /_/ / _  ___ / /_/ /_  /_/ / /_/ /_(__  )/  __/
/_/  /_/  /_____/  \____/  /_/  |_\__,_/ /_.___/\__,_/ /____/ \___/ 
````
# Warning: this program should never be used by anyone
# I am not responsible for any violations of the mega TOS
In her current state this program only really supports bulk uploading of mostly the same file types.  
It skips json files by default. It does not respect folder hierarchy.  
So if you have a folder containing multiple subfolders with for example jpeg's.  
It will dump all the contents of the different subfolders into the MEGA root.  
  
The program is tested and originally intended to be used with: pictures, videos, pdf's, and zip files.  
And will not play nice with more complex folder structures like a .git directory.  
  
If you know a nice feature, wanna fix one of the above mentioned limitations or implement something from the todo list.   
PR's are always welcome :)
## Install instructions
### Ubuntu
```bash
git clone git@github.com:11philip22/MEGAabuse.git
sudo apt update
sudo apt install libpcrecpp0v5
sudo ln -s /usr/lib/x86_64-linux-gnu/libpcre.so.3 /usr/lib/x86_64-linux-gnu/libpcre.so.1
chmod +x MEGAabuse/binaries/megacmd_linux/*
chmod +x MEGAabuse/binaries/megatools_linux/*
chmod +x MEGAabuse/MEGAabuse.py
```
This is what i needed to do to get it to work on Ubuntu 20.04.2.  
If you are getting errors related to either megacmd or megatools like the one below.
```
Traceback (most recent call last):
  File "MEGAabuse.py", line 348, in <module>
    upload_manager(upload_queue)  # Start Upload process
  File "MEGAabuse.py", line 285, in upload_manager
    results = pool.map(worker, queue)  # Map pool to upload queue
  File "/usr/lib/python3.8/multiprocessing/pool.py", line 364, in map
    return self._map_async(func, iterable, mapstar, chunksize).get()
  File "/usr/lib/python3.8/multiprocessing/pool.py", line 771, in get
    raise self._value
subprocess.CalledProcessError: Command '/home/philip/Devel/MEGAabuse/binaries/megatools_linux/megatools reg ...' returned non-zero exit status 126.
```
Manually run the command from ``CalledProcessError`` in your shell and see what packages you are missing/
### Arch
```
coming soon
```
### Debian
```
coming soon
```
## Usage
``./MEGAabuse.py -h``  
``./MEGAabuse.py -d <path to folder i want to upload>``  
``./MEGAabuse.py -d <path to folder i want to upload> <second path> <more paths>``
## Todo
- [ ] Full windows support
- [ ] MacOS support
- [ ] Keep sub-folder hierarchy
- [ ] Compile the latest bins or remove them from project
## Acknowledgements
- https://github.com/ncjones/python-guerrillamail
