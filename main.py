from flask import Flask, request, Response
from flask import render_template
app = Flask(__name__)

import datetime
import json
import os

from services.setup import SetUp
from services.config import Config
from services.executor import Executor

"""
    Routes for Rendering Page
"""
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/setup')
def setup():
    return render_template('setup.html', Config = Config)

@app.route('/execute', methods=["POST", "GET"])
def execute():
    worker_ui = {}
    for index in range(int(Config.numWorker)):
        worker_ui[str(index+1)] = """
            http://localhost:{}
        """.format( str(8081+index) )
    return render_template('execute.html', worker_ui = worker_ui)

"""
    Routes to trigger functions
"""
@app.route('/save_deploy_settings', methods=['POST'])
def save_deploy_settings():
    
    Config.dckLoc = request.form['dckLoc']
    Config.dckCmpsLoc = request.form['dckCmpsLoc']
    Config.numWorker = request.form['numWorker']
    
    return render_template('setup.html', Config = Config)

@app.route('/save_kafka_settings', methods=['POST'])
def save_kafka_settings():
    
    Config.topic = request.form['topic']
    Config.partition = request.form['partition']
    Config.replication = request.form['replication']
    Config.streamRate = request.form['streamRate']
    
    return render_template('setup.html', Config = Config)

@app.route('/launch_containers')
def launch_containers():
            
    setup = SetUp()
                     
    return Response(
        stream( setup.launch_containers ),
        mimetype='text/event-stream')

@app.route('/stop_containers')
def stop_containers():
            
    setup = SetUp()
                     
    return Response(
        stream( setup.stop_containers ),
        mimetype='text/event-stream')

@app.route('/delete_containers')
def delete_containers():
            
    setup = SetUp()
                     
    return Response(
        stream( setup.delete_containers ),
        mimetype='text/event-stream')
    
@app.route('/upload_file', methods=["POST", "GET"])
def upload_file():
    setup = SetUp()
    files = request.files.getlist("dataset_input")
    for file in files:
        setup.upload_file(file=file)
    return "{}"

@app.route('/execute/run_strider')
def run_strider():
    
    executor = Executor()
        
    return Response(
        stream(executor.strider_query),
        mimetype='text/event-stream')

@app.route('/run_producer')
def run_producer():
    
    executor = Executor()
        
    return Response(
        stream(executor.run_producer),
        mimetype='text/event-stream')

@app.route('/import_query', methods=['POST'])
def import_query():
    
    query_id = request.form['query_id'] 
    
    with open('{}/services/query/Query {}.txt'.format(os.getcwd(), query_id)) as file:
        query = file.read()
    
    res = {}
    res['query'] = query
    
    return json.dumps(res)

@app.route('/save_query', methods=['POST'])
def save_query():
    
    Config.query = request.form['query'] 
    
    print(Config.query)
    
    return '{}'

# Stream the python yield result
def stream(methodToRun):
    for line in methodToRun() :
        yield """
            retry: 10000\ndata:{"time":"%s", "message":%s}\n\n
        """ % ( datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        '"{}"'.format( line.rstrip() ))

if __name__ == '__main__':
    app.run(debug=True)