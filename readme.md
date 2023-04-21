# micropython-magic

This is a collection of magic methods for micropython for use with Jupyter (formerly IPython Notebook)

**This is a work in progress.**

Ref:
 - https://code.visualstudio.com/docs/datascience/jupyter-notebooks


## Installation
- create and activate a venv `python3 -m venv .venv`
-  `pip install -U "git+https://github.com/josverl/micropython-magic"`


## Usage

Create a notebook 

Load the magic

```python
%load_ext micropython_magic
```

turn on the led on pin 25 on the first connected device 
```python
%%micropython  
from machine import Pin
led = Pin(25, Pin.OUT)
led.value(1)
```

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

- but how to enable this for cell magics %%micropython ? [#1](https://github.com/Josverl/micropython-magic/issues/1)
  there seems to be some way provisioned for this using the #! notation 
- https://github.com/microsoft/vscode-jupyter/blob/27174e1ce07b51e312f698bef81dd453f533e8fd/src/interactive-window/editor-integration/codeGenerator.ts#L76-L108## Work in progress 


Recommended : install stubs 
- install stubs for MicroPython syntax checking `pip install micropython-esp32-stubs`


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
   - [/] is there a way to autoload a notebook with the magic ?
       https://github.com/ipython/ipython/issues/13493
       https://github.com/ipython/ipython/pull/13506
       `def register_lazy(self, name: str, fully_qualified_name: str):` ?
       `ip.magics_manager.register_lazy("lazy_line", Path(tf.name).name[:-3])`
       ```
            IPython 7.32
            ============
            The ability to configure magics to be lazily loaded has been added to IPython.
            See the ``ipython --help-all`` section on ``MagicsManager.lazy_magic``.
            One can now use::
                c.MagicsManger.lazy_magics = {
                        "my_magic": "slow.to.import",
                        "my_other_magic": "also.slow",
                }
            And on first use of ``%my_magic``, or corresponding cell magic, or other line magic,
            the corresponding ``load_ext`` will be called just before trying to invoke the magic.
       ```
   - [x] get the output from the MCU into a python variable `local = %eval remote`
         - eval is not quite the same as mpremote
         - retain type through json ?
         - [?] can this be done with repr(insted) of json ?
   - [x] plot data from a MCU
            - using bqplot ( > pyplot > vscode-Jupyter) 
            - add documentation / sample
-   
   - [ ] copy/echo MCU global vars to local vars ( sync_from / sync_to)?
   - [ ] get a data series onto the notebook and plot the outcome 
       - [x] loop one by one and update plot
       - [ ] get larger series 
   - [ ] loop and update plot 
         https://ipywidgets.readthedocs.io/en/7.x/examples/Widget%20Asynchronous.html#Updating-a-widget-in-the-background
   - [ ] long running via mqtt / async / folder mount ?
 - [ ] is there a way to avoid needing to set %%micropython on all cells ?
 - [ ] %timeit / %%timeit for micropython code 

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

