from flask_api import FlaskAPI
from flask import request
import docker
import sqlite3
import random
from flask_sqlalchemy import SQLAlchemy

app = FlaskAPI(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/aditya/Projects/nvie_agent/nvie.agent'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
client = docker.from_env()
db = SQLAlchemy(app)

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
    print(port_list)
    port = random.randrange(10000, 65534)
    while port in port_list:
        port = random.randrange(10000, 65534)
    print(port)
    try:
        print("Pulling art")
        old_port = params['port']
        env_name = params['env_name']
        print("Pulling")
        client.images.pull(params['image_name'])
        print("Pulled")
        container = client.containers.run(params['image_name'], detach = True, ports = {str(params['port'])+"/tcp":port})
        mapping = ContainerPortMapping(env_name = env_name, container = container.id, port = port, old_port = old_port)
        db.session.add(mapping)
        db.session.commit()
        print("Created Container")
    except Exception as e:
        return {'status':False}
    return {'status':True,'container_id':container.id, 'container_name':container.name, "image_name":container.image.tags[0]}

@app.route('/stop', methods=['POST'])
def stop():
    params = request.data
    mapping_list = ContainerPortMapping.query.filter_by(env_name = params['env_name']).first()
    container = client.containers.get(mapping_list.container)
    db.session.delete(mapping_list)
    container.stop()
    db.session.commit()
    return {'status':True, 'container_id':container.id, 'container_name':container.name, "image_name":container.image.tags[0],'env_name':params['env_name']}

@app.route('/stop-all', methods=['GET'])
def stopall():
    try:
        containers = client.containers.list()
        running_containers = []
        for i in containers:
            mapping_list = ContainerPortMapping.query.filter_by(container = i.id).first()
            running_containers.append({'container_name':i.name, 'container_id':i.id, "image_name":i.image.tags[0], 'env_name':mapping_list.env_name})
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
        running_containers.append({'container_name':i.name, 'container_id':i.id, "image_name":i.image.tags[0], 'env_name':mapping_list.env_name})
    # container.stop()
    return {'status':True, 'running':running_containers}

if __name__=='__main__':
    db.create_all()
    app.run(debug = True)

