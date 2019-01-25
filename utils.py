# -*- coding: utf-8 -*-
import os, logging, re, traceback, sys
import requests
#
#
import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

_SESSION = requests.Session()

class EmptyDataException(Exception): pass

class Switch(object):
    """SWITCHER"""
    def __init__(self, value):
        self.value = value
        self.fall = False

    def __iter__(self):
        yield self.match
        raise StopIteration

    def match(self, *args):
        if self.fall or not args:
            return True
        elif self.value in args:
            self.fall = True
            return True
        return False


def get_request(url):
    """Send get request & return data"""
    while(True):
        resp = None
        try:
            resp = _SESSION.get(url)
            if resp.status_code != 200:
                settings.print_message("HTTP Error #{0}. {1}.".format(resp.status_code, resp.reason))
                return None
            return resp.content
        except Exception as error:
            logger.warn(traceback.format_exc())
            settings.print_message(error)
            if input("Try load again? [y/n]: ") == 'y': continue
            return None
    return None

SEX = [
    "---",
    "Женский",
    "Мужской"
    ]