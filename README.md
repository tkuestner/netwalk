# netwalk
A clone of the famous netwalk game using Python3 & Kivy

![board](screenshots/example1.png "Game board")

## Installation

### Linux

* Clone this repository or download it as a ZIP file.
* Install Python >= 3.3 from your distro's package manager.
* Install Kivy from the package manager or follow these  [detailed instructions](https://kivy.org/docs/installation/installation-linux.html). (The package is often called python-kivy or python3-kivy.)
* If you are going to do development, consider using [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/).
* Edit `~/.kivy/config.ini` to set these values:
```
[kivy]
exit_on_escape = 0
...
[input]
mouse = mouse,disable_multitouch
```
* Start the game: `python3 netwalk.py`

### Windows

* Clone this repository or download it as a ZIP file.
* Download the latest Python3 version from [here](https://www.python.org/downloads/) .
* When installing, make sure to check "Add Python to PATH".
* Open a command line (cmd.exe) and type in the following commands (more [detailed instructions](https://kivy.org/docs/installation/installation-windows.html)):
```
python -m pip install --upgrade pip wheel setuptools
python -m pip install docutils pygments pypiwin32 kivy.deps.sdl2 kivy.deps.glew
python -m pip install kivy
```
* Edit `C:\Users\{username}\.kivy\config.ini` to set these values:
```
[kivy]
exit_on_escape = 0
...
[input]
mouse = mouse,disable_multitouch
```
* `cd` into the netwalk directory and start the game: `python netwalk.py`

## Gameplay

* Left mouse button: Rotate tile (counter-clockwise)
* Right mouse button: Lock tile
