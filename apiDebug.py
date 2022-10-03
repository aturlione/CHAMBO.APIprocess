from flask import Flask, request
from flask_restx import Api, Resource
import geo_process

app = Flask(__name__, instance_relative_config=True)
apiflask = Api(app, version="0.0.6", title="CHAMBO")

geo_process.start(apiflask)