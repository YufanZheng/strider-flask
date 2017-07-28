import docker
from os.path import expanduser

from .config import Config

class Executor():
    
    def __init__(self):
        self.directory = expanduser("~") + "/Documents/strider"
        self.dataDir = self.directory + '/data'
        self.client = docker.from_env()
        
    def kafka_consumer(self):
        # Get Spark Worker Container
        container = self.getContainerByName("strider_spark-master_1")
        
        # Extract the kafka configuration to cretae command
        command = """
            spark-submit 
                --master spark://spark-master:7077 
                --class sparkStreaming.Receiver 
                kafkaConsumer.jar 
                172.17.0.3:9092 
                {} 
                {}
        """.format( Config.topic, Config.partition )
        
        print(command)
        
        for line in container.exec_run(command, stream=True):
            yield line.decode('utf-8')
    
    def kafka_producer(self):
        pass
    
    def strider_query(self):
        pass
    
    def getContainerByName(self, name):
        
        for container in self.client.containers.list():
            if container.name == name:
                return container
            
        return None