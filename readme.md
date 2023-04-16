# micropython-magic

This is a collection of magic methods for micropython for use with Jupyter (formerly IPython Notebook)

**This is a work in progress.**

Ref:
 - https://code.visualstudio.com/docs/datascience/jupyter-notebooks


## Installation
- create and activate a venv `python3 -m venv .venv`
-  `pip install -U "git+https://github.com/josverl/micropython-magic"`

Recommended : install stubs 
- install stubs for MicroPython syntax checking `pip install micropython-esp32-stubs`


 - [x] run a code cell on a MCU 
 - [ ] mpremote primitives
   - [x] list connected boards and loop through them 
   - [x] switch the active MCU
   - [x] avoid resetting MCU between cells ( use `resume`)
   - [ ] soft & hard reset a MCU
   - [ ] direct - copy file / files to / from 
   - [ ] ls and other file operations 
   - [ ] wipe files from MCU 
   - [ ] mip install 
   - [ ] reset a MCU
 - [ ] Notebook essentials
   - [ ] load magics from `pip install micropython-magic`
   - [ ] get the output from the MCU into a python variable 
   - [ ] plot data from a MCU
   - [ ] copy/echo MCU global vars to local vars ?
   - [ ] get a data series onto the noteboot and plot the outcome 
   - [ ] long running via mqtt ?
 - [ ] automagic to avoid needing to set %%micropython onall cells
 - [ ] Samples 
   - [ ] blink
   - [ ] list connected boards an d loop through them 
   - [ ] read sensand build series 
   - [ ] flash a mcu ( sample per port )

## Usage

Create a notebook 

Load the magic

```python
%load_ext micropython-magic
```

turn on the tled connected to pin 25 on the first connected device 
```python
%%micropython  
from machine import Pin
led = Pin(25, Pin.OUT)
led.value(1)
```

## Advanced 
List the connected devices 
```python
%list
```

