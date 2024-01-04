
# initial 

 - [x] run a code cell on a MCU 
 - [x] mpremote primitives
   - [x] list connected boards and loop through them 
   - [x] switch the active MCU
   - [x] avoid resetting MCU between cells ( use `resume`)
   - [x] soft-reset a MCU
   - [/] hard-reset a MCU
       - only works on non-rp2040 devices 
       - report / fix hardware reset  issue on rp2040 `machine.reset()` ?
   - [x] mount folder 
   - [?] recursive delete wipe files from MCU - as a built-in magic ? / wait for / create PR for mpremote update ?
   - [x] cellmagic to copy cell content to specific files on the MCS 
       - [x] %%micropython --writefile main.py
       - [x] %%micropython --readfile boot.py


   **`!mpremote` can be use to run any other command**
   - [x] **`!mpremote`** mip install 
   - [x] direct - copy file / files to / from 
   - [x] ls and other file operations 
- [ ] Notebook essentials
   - [x] load magics from `%pip install micropython-magic`
   - [x] get the output from the MCU into a python variable `local = %eval remote`
         - eval is not quite the same as mpremote
         - [x] retain type through json - works for the majority of standard types
         - [?] can this be done with repr(instead) of json ?
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
       this could be done via an input_transformer - but keeping the state between cells may be quite hard / confusing
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

  - [x] Local on windows
    - [x] on windows 
    - [x] on linux
    - [ ] on MacOS
  - Manual test:
    - [x] jupyter notebook
    - [x] jupyter labs 

  - [ ] CI - using WOKWI as a device simulator ? 
        Blocked as WOKWI CI does not implement serial connection

