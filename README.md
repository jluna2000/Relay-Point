# Relay Point
This project aims to create a relay server from a machine with a source drive to any given client machine. This is to provide a remote access alternative to using/making a NAS and opening router to the public.

## To run the server

``` bash
# ~ Start guide (make sure to go through each step)~

# make sure to install pip
python -m pip install --upgrade pip

# for windows users: create a python enviroment
py -m venv venv
 
# for mac users:
python3 -m venv venv
 
# Activating python enviroment on windows
.\venv\Scripts\activate

# Activating python environment on mac
source venv/bin/activate

# install the dependencies
python -m pip install -r requirements.txt or pip3 install -r requirements.txt

# now you can run the server.py  (the google/flask dependencies are installed)
python app.py

# to leave the python virtual environment/deactivate it
deactivate
```
