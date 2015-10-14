import logging

class Logger:
    def __init__(self):
        self.format = '%(asctime)s - %(funcName)s - %(levelname)s - %(message)s'
        logging.basicConfig(filename='./logger/log', 
                            format=self.format,
                            filemode='w',
                            level=logging.INFO)
        self.log = logging

        
logger = Logger()
log = logger.log
        