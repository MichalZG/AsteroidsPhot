#configuration file handler
import ConfigParser
import os

class Config:
    def __init__(self):
        config = ConfigParser.RawConfigParser()
        config.read('./config/config.cfg')
        self.config = config

        # files
        self.file_extension = config.get('files', 'file_extension')
        self.file_path = config.get('files', 'file_path')
        self.telescope_config_path = config.get('files' , 'telescope_config_path')

        # headers
        config.read(self.telescope_config_path)
        self.target = config.get('headers', 'target')
        self.exptime = config.get('headers', 'exptime')
        self.obsdate = config.get('headers', 'obsdate')
        self.telescope = config.get('headers', 'telescope')
        self.ra = config.get('headers', 'ra')
        self.dec = config.get('headers', 'dec')
        self.jd = config.get('headers', 'jd')
    
    def reconf(self):
        self.__init__()

cfg = Config()
