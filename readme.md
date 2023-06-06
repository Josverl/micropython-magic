# micropython-magic

This is a collection of magic methods for micropython for use with Jupyter (formerly IPython Notebook)

**This is a work in progress.**

Ref:
 - https://code.visualstudio.com/docs/datascience/jupyter-notebooks


## Installation
- create and activate a venv `python3 -m venv .venv`
-  `pip install -U "git+https://github.com/josverl/micropython-magic"`


## Usage

**1) Create a notebook**

**2) Load the magic**
```python
%load_ext micropython_magic
```
This can also be configured once to always load automatically ( see below)




**3) add a cell with some code to run on the MCU**
```python
%%micropython  
from machine import Pin
led = Pin(25, Pin.OUT)
led.value(1)
```
The `%%micropython` cell magic will instruct Jupyter to run the code on the connected MCU

**4) enable code highlighting for MicroPython**
```python
%pip install micropython-esp32-stubs==1.20.0.*
# installs the stubs for MicroPython syntax checking (one time install per environment) 
```

```python
# %%micropython  
from machine import Pin
led = Pin(25, Pin.OUT)
led.value(1)
```
This allows for syntax highlighting and code completion of MicroPython code.
Tested in VSCode with
- [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) extension
- [Pylance](https://marketplace.visualstudio.com/items?itemName=ms-python.vscode-pylance) extension


## Advanced 
List the connected devices 
```python
%list_devices
```

## Automatically load the magic on startup

In order to automatically load the magic on startup, you can add the following to your `ipython_config.py` file:

- create a ipython profile 
  - `ipython profile create`
  - add the following to the configuration file (`.../.ipython/profile_default/ipython_config.py`)

    ```python
    c = get_config()  #noqa

    c.InteractiveShellApp.extensions = [
        'micropython_magic'
    ]
    ```

# Pylance for Jupyter Notebooks

https://github.com/microsoft/vscode-jupyter/wiki/Intellisense-for-notebooks


Recommended : install stubs 
- [x] install stubs for MicroPython syntax checking `pip install micropython-esp32-stubs`


 - [x] run a code cell on a MCU 
 - [ ] mpremote primitives
   - [x] list connected boards and loop through them 
   - [x] switch the active MCU
   - [x] avoid resetting MCU between cells ( use `resume`)
   - [x] soft-reset a MCU
   - [/] hard-reset a MCU
       - only works on non-rp2040 devices 
       - report / fix hardware reset  issue on rp2040 `machine.reset()` ?
   - [ ] mip install 
   - [ ] direct - copy file / files to / from 
   - [ ] mount folder 
   - [ ] ls and other file operations 
   - [ ] recursive delete wipe files from MCU - as a built-in magic ? / wait for / create PR for mpremote update ?
   - [ ] cellmagic to copy cell content to specific files on the MCS 
       - [ ] %%copy_to_mcu main.py
       - [ ] %%copy_to_mcu boot.py
- [ ] Notebook essentials
   - [x] load magics from `%pip install micropython-magic`
   - [x] get the output from the MCU into a python variable `local = %eval remote`
         - eval is not quite the same as mpremote
         - retain type through json ?
         - [?] can this be done with repr(insted) of json ?
   - [x] plot data from a MCU
            - [x] using bqplot ( > pyplot > vscode-Jupyter) 
            - [/] add documentation / sample
-   
   - [ ] copy/echo MCU global vars to local vars ( sync_from / sync_to)?
   - [ ] get a data series onto the notebook and plot the outcome 
       - [x] loop one by one and update plot
       - [ ] get larger series 
   - [ ] loop and update plot 
         https://ipywidgets.readthedocs.io/en/7.x/examples/Widget%20Asynchronous.html#Updating-a-widget-in-the-background
   - [ ] long running via mqtt / async / folder mount ?
 - [ ] is there a way to avoid needing to set %%micropython on all cells ?
       this could be done via an input_transformer - but keeping the state between cells may be quuite hard / confusing
 - [ ] %timeit / %%timeit for micropython code to avoid measuring the mpremote startup overhead 

Samples
   - [x] Install
   - [x] basic board control
   - [x] blink
   - [x] list connected boards and loop through them 
   - [~] read sensor and build series ( file / list / plot)
   - [ ] flash a mcu with new firmware ( sample per port )
   - [ ] mip install 
   - [ ] upload a repo / folder to a MCU

## development
## Testing 

- using Pytest
- using testbook for testing notebooks
  - located in the `./tests/` folder
  - tests are paired with notebooks that contain the cells and magic commands to be tested
  - tests have not been mocked - and therefore require a connected MCU to run ( rp2040 )

- TODO: add tests for (remote) kernels 
  - [x] Local (on windows)
  - [ ] on windows 
  - [ ] on linux
  - [ ] jupyter notebook
  - [ ] jupyter labs 

