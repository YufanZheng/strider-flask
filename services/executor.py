import docker
from os.path import expanduser

from .config import Config

class Executor():
    
    def __init__(self):
        self.directory = expanduser("~") + "/Documents/strider"
        self.dataDir = self.directory + '/data'
        self.client = docker.from_env()
    
    def run_producer(self):
        
        yield "Creating Kafka Topic {} at Kafka Container".format( Config.topic )
        for line in self.create_topic():
            yield line
        
        yield "Launching Producer"
        for line in self.run_kafka_producer():
            yield line
        
        yield "Producer has been started"
    
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
        
    def run_kafka_producer(self):
        # Get Spark Worker Container
        container = self.getContainerByName("strider_spark-master_1")
        
        # Extract the kafka configuration to cretae command
        command = """
            java 
                -jar kafkaProducer.jar 
                {} 
                172.17.0.3:9092
                {} 
                {}
        """.format( Config.kafkaSrcFile, Config.topic, Config.partition )
        
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