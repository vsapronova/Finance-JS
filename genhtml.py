from flask import Flask
import os
from jinja2 import Environment, FileSystemLoader

app = Flask(__name__)

env = Environment(loader=FileSystemLoader('templates'))

rootdir = './templates'

new_dir = './www'

for file in os.listdir(rootdir):
    template_path = os.path.join(rootdir, file)
    print(template_path)
    template = app.jinja_env.get_or_select_template(file)
    output = template.render()

    if not os.path.exists(new_dir):
        os.makedirs(new_dir)

    output_path = os.path.join(new_dir, file)
    with open(output_path, "w") as f:
        f.write(output)