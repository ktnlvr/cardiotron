git submodule update --recursive --remote
python -m mpremote cp -r src/. :
python -m mpremote cp -r external/metropolia-pico-lib :lib
python -m mpremote rtc --set
python -m mpremote run ./src/main.py
