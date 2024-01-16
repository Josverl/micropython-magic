# Tests for micropython_magic

The tests are intended to be run using pytest or using the VSCode python test runner.

Note that the majority of test require interaction with a MCU, and therefore can not be run in CI (github actions).
I have not spend the time required to mock the mpremote and MCU interaction, but it should be possible if someone is willing to spend the time to build, and maintain such mocked tests.


Most of the test make use of [*testbook*](https://testbook.readthedocs.io/en/latest/index.html), a unit testing framework for testing code in Jupyter Notebooks.

 * *test_samples.py* verify all the samples in the samples folder are working. (using testbook)
 * *testbook_cases* - testbook tests that are fully coded as notebooks, and are located in the `test/testbook_cases` folder.
 * *testbook_coded* - pytest test using testbook that are coded in the traditional way, and are located in the `tests/testbook_coded` folder.
   for each foo_test.py there is a foo_test.ipynb that is the notebook that is used by the.
 * some other tests are coded in the traditional way, and are located in the `tests` folder.

