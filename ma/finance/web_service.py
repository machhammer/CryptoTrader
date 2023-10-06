from flask import Flask
from flask_cors import CORS
import service_controller as service_controller

app = Flask(__name__)
CORS(app)


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route("/news")
def news():
    return service_controller.news()
