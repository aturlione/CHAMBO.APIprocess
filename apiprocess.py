from flask import Flask, request
from flask_restx import Api
import geo_process
from flask_cors import CORS


app = Flask(__name__, instance_relative_config=True)
CORS(app)
apiflask = Api(app, version="0.0.6", title="CHAMBO ApiProcess")


def create():
    geo_process.start(apiflask)
    return app


if __name__ == "Model":
    create()