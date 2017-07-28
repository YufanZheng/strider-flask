import subprocess
from os.path import expanduser
import os
import shutil
import docker
import tarfile
from io import BytesIO
from werkzeug.utils import secure_filename
import time

from .config import Config

class SetUp():
    
    def __init__(self):
        self.directory = expanduser("~") + "/Documents/strider"
        self.dataDir = self.directory + '/data'
        self.client = docker.from_env()
    
    """
        Launch Containers:
            1. Docker compose to start containers
            2. In Kafka container, create topic
    """    
    
    def launch_containers(self):
        
        yield "Start launching containers"
        for line in self.docker_compose_up():
            yield line

        yield "Creating Kafka Topic {} at Kafka Container".format( Config.topic )
        for line in self.create_topic():
            yield line
        
        yield ""
        yield "Deploying process is finished"

    """
        Stop Containers:
            1. Docker compose to stop running containers
    """    
    
    def stop_containers(self):
        
        yield "Stop running containers"
        for line in self.docker_compose_stop():
            yield line
        
        yield ""
        yield "All containers have been stopped"

    """
        Delete Containers:
            1. Docker compose to delete running containers
    """    
    
    def delete_containers(self):
        
        yield "Delete containers"
        for line in self.docker_compose_down():
            yield line
        
        yield ""
        yield "All containers have been removed"

    """
        Docker Compose:
            1. Create an empty directory at /{user.home}/Documents/strider
            2. Copy strider Dockerfiles to strider directory
            3. Generate the docker-compose.yml file 
            4. Run "docker-compose up -d" command to create containers
    """    
    def docker_compose_up(self):

        # Copy all the rest into strider path without "docker-compose.yml"
        # Strider path
        self.createDir( self.directory )
        self.createDir( self.dataDir )
        # Strider docker path
        source_folder = os.path.join(os.path.dirname(__file__), 'strider-docker')
        self.copyDir(source_folder, self.directory)
        
        # Create docker-compose.yml file at strider folder
        self.generateDckCmpsFile( int( Config.numWorker ), self.directory )
        
        # Execute command
        command = Config.dckCmpsLoc + " -f " + self.directory + "/docker-compose.yml up -d"
        
        return self.runProcess(command.split())
    
    def createDir(self, directory):
        # Set strider directory at /{user.home}/Documents/strider
        
        if os.path.exists(directory):
            # Empty the directory if already exists
            shutil.rmtree(directory)
            
        os.makedirs(directory)
    
    def copyDir(self, src, dst):
        # Copy folder from src to dst
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, False, None)
            else:
                shutil.copy2(s, d)
    
    def generateDckCmpsFile(self, numWorkers, directory):
        
        dckCmpsFile = ""
        appendix = ""
        
        # Read the docker-compose.yml file without the part of spark worker
        with open(
                os.path.join(os.path.dirname(__file__), 
                        'strider-docker-compose/docker-compose-without-spark-worker.yml'), 
                'r') as file:
            dckCmpsFile = file.read()
        
        # Read the docker-compose.yml file of only the spark worker part
        with open(
                os.path.join(os.path.dirname(__file__), 
                        'strider-docker-compose/docker-compose-spark-worker.yml'), 
                'r') as file:
            appendix = file.read()
            # Add as many as needed of spark workers
            while numWorkers > 0 :
                # Replace with different hostname and port
                dckCmpsFile = dckCmpsFile + "\n\n" + appendix.replace(
                        "spark-worker-port", 
                        (str) (8080 + numWorkers), 4).replace(
                        "spark-worker-name", 
                        "spark-worker-" + (str) (numWorkers), 2)
                numWorkers = numWorkers - 1
        
        with open( directory + "/docker-compose.yml", "w") as file: 
            file.write(dckCmpsFile) 
    
    def runProcess(self, exe):    
        self.stdouts = []
        p = subprocess.Popen(exe, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        while(True):
            retcode = p.poll() #returns None while subprocess is running
            line = p.stdout.readline()
            yield line.decode('utf-8').rstrip() 
            if(retcode is not None):
                break
    
    def getContainerByName(self, name):
        
        for container in self.client.containers.list():
            if container.name == name:
                return container
            
        return None
    
    """
        Create Kafka Topic:
            1. Find the Kafka container by name
            2. Execute command in this container to create topic
            3. Return streaming result
    """
    def create_topic(self):
        
        # Get Kafka Container
        container = self.getContainerByName("strider_kafka_1")
        
        # Extract the kafka configuration to cretae command
        command = """
            kafka/bin/kafka-topics.sh 
                --create --zookeeper 172.17.0.2:2181 
                --replication-factor {}
                --partitions {} 
                --topic {}
        """.format( Config.replication, Config.partition, Config.topic )
        
        for line in container.exec_run(command, stream=True):
            yield line.decode('utf-8')

    """
        Stop running containers:
            1. Find the docker-compose file location
            2. Docker compose stop
    """
    def docker_compose_stop(self):
        # Execute command
        command = Config.dckCmpsLoc + " -f " + self.directory + "/docker-compose.yml stop"
        
        return self.runProcess(command.split())

    """
        Stop running containers and delete images:
            1. Find the docker-compose file location
            2. Docker compose down
    """
    def docker_compose_down(self):
        # Execute command
        command = Config.dckCmpsLoc + " -f " + self.directory + "/docker-compose.yml down"
        
        return self.runProcess(command.split())
    
    """
        Save Upload Files:
            1. Find the Kafka container by name
            2. Execute command in this container to create topic
            3. Generate tar stream for kafkaConsumer.jar & kafkaProducer.jar
            4. Use Docker API to put it into conainser
    """
    def upload_file(self, file):
        filename, filepath = self.saveFile(file)
        
        # Get Spark Worker Container
        container = self.getContainerByName("strider_spark-master_1")
        
        # Upload Kafka Consumer
        tarstream = self.toBytes( filename, filepath )
        tarstream.seek(0)
        container.put_archive(
            path='/usr/local',
            data=tarstream
        )
    
    def toBytes(self, filename, filepath):
        
        data = bytes()
        with open(filepath, "rb") as file:
            data = file.read()
        
        #write data to tarstream
        tarstream = BytesIO()
        tar = tarfile.TarFile(fileobj=tarstream, mode='w')
        tarinfo = tarfile.TarInfo(name=filename)
        tarinfo.size = len(data)
        tarinfo.mtime = time.time()
        #tarinfo.mode = 0600
        tar.addfile(tarinfo, BytesIO(data))
        tar.close()
        
        return tarstream
    
    def saveFile(self, file):
        filename = secure_filename(file.filename)
        filepath = os.path.join(self.dataDir, filename)
        file.save(filepath)
        return filename, filepath