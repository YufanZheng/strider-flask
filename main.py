from flask import Flask, request, Response
from flask import render_template
app = Flask(__name__)

import datetime

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

@app.route('/execute/<appname>', methods=["POST", "GET"])
def execute(appname):
    worker_ui = {}
    for index in range(int(Config.numWorker)):
        worker_ui[str(index+1)] = """
            http://localhost:{}
        """.format( str(8081+index) )
    return render_template('execute.html', appname = appname, worker_ui = worker_ui)

"""
    Routes to trigger functions
"""
@app.route('/saveSettings', methods=['POST'])
def save_settings():
    
    Config.dckLoc = request.form['dckLoc']
    Config.dckCmpsLoc = request.form['dckCmpsLoc']
    Config.numWorker = request.form['numWorker']
    Config.topic = request.form['topic']
    Config.partition = request.form['partition']
    Config.replication = request.form['replication']
    
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

@app.route('/execute/<appname>/run')
def run_app(appname):
    
    executor = Executor()
    methodToRun = None
    
    if appname == "Kafka Producer":
        methodToRun = executor.kafka_producer
    elif appname == "Kafka Consumer":
        methodToRun = executor.kafka_consumer
    elif appname == "Strider Query":
        methodToRun = executor.strider_query
        
    return Response(
        stream(methodToRun),
        mimetype='text/event-stream')

# Stream the python yield result
def stream(methodToRun):
    for line in methodToRun() :
        yield """
            retry: 10000\ndata:{"time":"%s", "message":%s}\n\n
        """ % ( datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        '"{}"'.format( line.rstrip() ))

if __name__ == '__main__':
    app.run(debug=True)