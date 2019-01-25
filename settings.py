# -*- coding: utf-8 -*-
import argparse
import collections
import os, logging, re, traceback, sys
import json
from datetime import datetime
import re
#
_main_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_main_dir, 'utils\\'))
sys.path.insert(0, os.path.join(_main_dir, 'entities\\'))
sys.path.insert(0, os.path.join(_main_dir, 'internet_resources\\'))
#

# VK Information
VK_APPLICATION_ID = "6303743"
VK_LOGIN = ""
VK_PASSWORD = ""
VK_GET_ACCESS_TOKEN_URL = r"https://oauth.vk.com/authorize?client_id=6303743&display=page&redirect_uri=https://oauth.vk.com/blank.html&scope=friends,photos,audio,video,docs,notes,pages,status,wall,groups,messages,notifications,offline&response_type=token"
VK_ACCESS_TOKEN = ""
VK_USER_ID = ""

VK_PHOTO_1 = "photo_100"
VK_PHOTO_2 = "photo_200"

SAVE_COUNT = 25
MAX_RETRY = 5

def build_version_string():
    """ This function read current version from version.txt and format version string """
    # MAJOR version when you make incompatible API changes
    __MAJOR_VERSION__ = str()
    # MINOR version when you add functionality in a backwards-compatible manner
    __MINOR_VERSION__ = str()
    # PATCH version when you make backwards-compatible bug fixes
    __PATCH_VERSION__ = str()
    with open('version.txt', 'r') as version_file:
        lines = version_file.readlines()
        for line in lines:
            if line.startswith('__MAJOR_VERSION__'):
                __MAJOR_VERSION__ = re.findall('\d+', line)[0]
            if line.startswith('__MINOR_VERSION__'):
                __MINOR_VERSION__ = re.findall('\d+', line)[0]
            if line.startswith('__PATCH_VERSION__'):
                __PATCH_VERSION__ = re.findall('\d+', line)[0]
    _header = "CrawlerVK (v{0}.{1}.{2}) {3}".format(__MAJOR_VERSION__, __MINOR_VERSION__, __PATCH_VERSION__,
                                                      datetime.now().strftime("%B %d %Y, %H:%M:%S"))
    return _header


# Program version
_header = build_version_string()

# system settings
#_DB_FILE = None
_LOGBOOK_NAME = None
_CONTROL_FILE = None
OUTPUT_FILE = None
#PROXY_FILE = None

INFO_FILE = None
LOG_LEVEL = logging.DEBUG
# encoding
OS_ENCODING = "utf-8"
OUTPUT_ENCODING = "utf-8"

CONTROL_KEYS = [
    "command",
    "user_id",
    "levels",
    "user_ids",
    ]

CONTROL_DEFAULT_VALUES = collections.defaultdict(lambda: str())
CONTROL_DEFAULT_VALUES = \
    {
        # "" : None,
        "max_processing_friends" : 450,
    }

# logging

# CONSOLE LOG
cfromat = "[{0}] {1}{2}"
def print_message(message, level=0):
    level_indent = " " * level
    print(cfromat.format(datetime.now(), level_indent, message))
#

# Logging handlers
class InMemoryHandler(logging.Handler):
    def emit(self, record):
        #print(self.format(record))
        IN_MEMORY_LOG.append(self.format(record))

_LOG_HANDLER = InMemoryHandler()
_LOG_FORMAT = "[%(asctime)s %(levelname)s %(name)s] %(message)s"
_LOG_COPY_FORMAT = "%(message)s"
_LOG_HANDLER.setFormatter(logging.Formatter(_LOG_FORMAT))

IN_MEMORY_LOG = []

main_logger = logging.getLogger("")

main_logger.addHandler(_LOG_HANDLER)
main_logger.setLevel(LOG_LEVEL)

logger = logging.getLogger(__name__)

print_message(_header)
logger.info(_header)

# Command line parser
logger.info("Initializing argument parser, version: %s" % argparse.__version__)
_parser = argparse.ArgumentParser()
requiredNamed = _parser.add_argument_group('Required arguments')
#requiredNamed.add_argument("-d", "--database", action="store", dest="DB_FILE_NAME", help="Database file", type=str, required=True)
requiredNamed.add_argument("-l", "--log", action="store", dest="LOG_FILE_NAME", help="Logbook file", type=str, required=True)
requiredNamed.add_argument("-c", "--control", action="store", dest="CONTROL_FILE_NAME", help="Control file", type=str, required=True)
requiredNamed.add_argument("-o", "--output", action="store", dest="OUTPUT_FILE", help="Output file", type=str, required=True)
#requiredNamed.add_argument("-p", "--proxies", action="store", dest="PROXIES_FILE", help="File with proxies", type=str, required=True)

logger.debug("Parse arguments.")

_command_args = _parser.parse_args()
#_DB_FILE = _command_args.DB_FILE_NAME
_LOGBOOK_NAME = _command_args.LOG_FILE_NAME
_CONTROL_FILE = _command_args.CONTROL_FILE_NAME
OUTPUT_FILE = _command_args.OUTPUT_FILE
#PROXY_FILE = _command_args.PROXIES_FILE

logger.info("Initializing logbook.")

# Add file handler
_LOG_F_HANDLER = logging.FileHandler(_LOGBOOK_NAME, encoding = OUTPUT_ENCODING)
_LOG_F_HANDLER.setLevel(LOG_LEVEL)
_LOG_F_FORMATTER = logging.Formatter(_LOG_COPY_FORMAT)
_LOG_F_HANDLER.setFormatter(_LOG_F_FORMATTER)

logger.debug("Copy startlog in logbook.")
main_logger.removeHandler(_LOG_HANDLER)
main_logger.addHandler(_LOG_F_HANDLER)
for record in IN_MEMORY_LOG:
    logger.info(record)

_LOG_F_FORMATTER = logging.Formatter(_LOG_FORMAT)
_LOG_F_HANDLER.setFormatter(_LOG_F_FORMATTER)

# Control file
logger.info("Parsing the control file.")
PARAMS = None
try:
    with open(_CONTROL_FILE) as data_file:    
        PARAMS = json.load(data_file)
    for key in PARAMS.keys():
        if not key in CONTROL_KEYS:
            raise Exception("Unknown parameter: {0}".format(key))
    # check all params, if null then set default
    for key in CONTROL_DEFAULT_VALUES.keys():
        PARAMS.setdefault(key, CONTROL_DEFAULT_VALUES[key]) 
except:
    print_message("Invalid file control. Check the syntax.")
    logger.error("Invalid file control. Check the syntax.")
    logger.error(traceback.print_exc())
    exit()
else:
    logger.info("Parsing was successful.")
print_message("Parameters:")
logger.debug("Parameters:")
for key in PARAMS.keys():
    param_str = "  {0} = '{1}'".format(key, PARAMS[key])
    print_message(param_str)
    logger.debug(param_str)
_SUCCESSFUL_START_FLAG = True