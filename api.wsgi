#!/usr/bin/python
# virtualenv api
activate_this = "/mnt/e/MASTER_DATA/TFM/Chambo/CHAMBO.Apiprocess/env_Linux/bin/python"
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))
import sys
import logging

logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, "/mnt/e/MASTER_DATA/TFM/Chambo/CHAMBO.Apiprocess")

# from FlaskApp import app as application
import apiprocess

# api = ApiProcess()
application=apiprocess.create()