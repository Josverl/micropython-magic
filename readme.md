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
   - [x] load magics from `%pip install micropython-magic`
   - [ ] is there a way to autoload a notebook with the magic ?
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
   - [ ] plot data from a MCU
   - [ ] copy/echo MCU global vars to local vars ( sync_from / sync_to)?
   - [ ] get a data series onto the noteboot and plot the outcome 
   - [ ] loop and update plot 
         (https://stackoverflow.com/questions/15635341/run-parts-of-a-ipython-notebook-in-a-loop-with-different-input-parameter)
   - [ ] long running via mqtt ?
 - [ ] is there a way to avoid needing to set %%micropython on all cells ?
   - [ ] blink
   - [ ] list connected boards and loop through them 
   - [ ] read sensor and build series ( file / list / plot)
   - [ ] flash a mcu with new firmware ( sample per port )
   - [ ] mip install 
   - [ ] upload a repo / folder to a MCU

## Usage

Create a notebook 

Load the magic

```python
%load_ext micropython_magic
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

