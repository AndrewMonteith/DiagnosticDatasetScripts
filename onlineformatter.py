#!/bin/python3
from flask import Flask,  request, render_template
import urllib
import subprocess

import flask

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("formatter.html")


def format_java_code(code):
    task = subprocess.run(["java", "-jar", "/home/monty/IdeaProjects/java-corpus/google-format.jar",
                           "-", "--skip-sorting-imports", "--skip-removing-unused-imports"],
                          input=code.encode("ascii"),
                          stdout=subprocess.PIPE)

    return task.stdout.decode("ascii")


@app.route('/format/', methods=['POST'])
def main():
    return format_java_code(request.get_json()["code"])


if __name__ == '__main__':
    app.run(debug=True)
