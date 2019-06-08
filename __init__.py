from flask_api import FlaskAPI
from flask import request
import docker
import sqlite3
import random
from flask_sqlalchemy import SQLAlchemy
import os
import subprocess
from urllib.parse import urlparse

app = FlaskAPI(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/aditya/Projects/nvie_agent/nvie.agent'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////home/ubuntu/nvie_agent/nvie.agent'
client = docker.from_env()
db = SQLAlchemy(app)

def uri_validator(x):
    try:
        result = urlparse(x)
        return True
    except:
        return False
class ContainerPortMapping(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    env_name = db.Column(db.String(100), unique=True, nullable=False)
    container = db.Column(db.String(100), unique=True, nullable=False)
    port = db.Column(db.Integer(), unique=True, nullable=False)
    old_port = db.Column(db.Integer(), nullable=False)

@app.route('/spawn', methods=['POST'])
def index():
    
    params = request.data
    port_list = ContainerPortMapping.query.with_entities(ContainerPortMapping.port).all()
    port = random.randrange(10000, 65534)
    while port in port_list:
        port = random.randrange(10000, 65534)
    try:
        old_port = params['port']
        env_name = params['env_name']
        client.images.pull(params['image_name'])
        path = ""
        if uri_validator(params['env_name']) and len(params['env_name'].split(".")) == 5:
            path = "/home/ubuntu/storage/"+params['env_name'].split(".")[0]+"-"+params['env_name'].split(".")[1]+"-"+params['env_name'].split(".")[2]
            # path = "/Users/aditya/Projects/nvie_agent/"+params['env_name'].split(".")[0]+"-"+params['env_name'].split(".")[1]
            try:
                os.mkdir(path)
                subprocess.call(['git','clone',params['gh_repo'], path])
                subprocess.call(['sudo','chmod', '-R', "777", path])
            except FileExistsError as e1:
                print(e1)
        else:
            return {'status':False, "desc":"Env Name not a valid env URL"}
        container = client.containers.run(params['image_name'], detach = True, ports = {str(params['port']):port}, volumes= {str(path):{'bind': '/home/nvie', 'mode': 'rw'}}, stdin_open = True, tty = True)
        mapping = ContainerPortMapping(env_name = env_name, container = container.id, port = port, old_port = old_port)
        db.session.add(mapping)
        conf = '''server {
    listen 80;
    server_name '''+str(env_name)+''';

    location / {
        proxy_pass http://localhost:'''+str(port)+''';
    }
}'''
        with open("/etc/nginx/conf.d/"+env_name+".conf", "w") as file:
            file.write(conf)
        subprocess.call(["sudo", "service", "nginx", "restart"])
        db.session.commit()
        print("Created Container")
    except Exception as e:
        print(e)
        return {'status':False}
    print({'status':True,'container_id':container.id, 'container_name':container.name})
    return {'status':True,'container_id':container.id, 'container_name':container.name}

@app.route('/stop', methods=['POST'])
def stop():
    try:
        params = request.data
        mapping_list = ContainerPortMapping.query.filter_by(env_name = params['env_name']).first()
        container = client.containers.get(mapping_list.container)
        db.session.delete(mapping_list)
        container.stop()
        db.session.commit()
    except Exception as e:
        return {'status':False}
    return {'status':True, 'container_id':container.id, 'container_name':container.name,'env_name':params['env_name']}

@app.route('/stop-all', methods=['GET'])
def stopall():
    try:
        containers = client.containers.list()
        running_containers = []
        for i in containers:
            mapping_list = ContainerPortMapping.query.filter_by(container = i.id).first()
            running_containers.append({'container_name':i.name, 'container_id':i.id, 'env_name':mapping_list.env_name})
            db.session.delete(mapping_list)
            i.stop()
            db.session.commit()
    except Exception as e:
        return {'status':False}
    return {'status':True, 'stopped':running_containers}

@app.route('/running', methods=['GET'])
def running():
    containers = client.containers.list()
    running_containers = []
    for i in containers:
        mapping_list = ContainerPortMapping.query.filter_by(container = i.id).first()
        env_name = ""
        if mapping_list:
            env_name = mapping_list.env_name
        running_containers.append({'container_name':i.name, 'container_id':i.id, 'env_name':env_name})
    # container.stop()
    return {'status':True, 'running':running_containers}

if __name__=='__main__':
    db.create_all()
    app.run(debug = True,host = '0.0.0.0')

