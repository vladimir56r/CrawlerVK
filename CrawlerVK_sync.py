# -*- coding: utf-8 -*-
import sys
import traceback
import logging
import os
import queue
import json
from datetime import datetime
import itertools
import time
from pygraphml import Graph
import vk
import requests
import os
from base64 import b64encode
#
import settings
import yEdGraph
import utils

logger = logging.getLogger(__name__)
logger.setLevel(settings.LOG_LEVEL)

def get_friends_graph():
    """ Get friends for users and create social graph. """
    total_users = 0
    count_bad_users = 0
    count_graph_users = 0

    result = "was successful"

    settings.print_message("Create VK session for application (app_id={})".format(settings.VK_APPLICATION_ID))
    logger.debug("Create VK session for application (app_id={}).".format(settings.VK_APPLICATION_ID))
    try:
        session = vk.Session(access_token=settings.VK_ACCESS_TOKEN)
        api = vk.API(session)
    except Exception as error:
        logger.warn(traceback.format_exc())
        settings.print_message("Can't create VK session for application with app_id={}".format(settings.VK_APPLICATION_ID))
        return ("with error.", 0, 0, 0)
    # logger.debug("".format())
    graph = yEdGraph.Graph()
    level_queue = [int(settings.PARAMS["user_id"]), ]
    count_levels = int(settings.PARAMS["levels"])
    all_level_ids = [list() for _ in range(count_levels)]

    for step in range(count_levels):
        settings.print_message("Process level #{} (total users {})".format(step, level_counter))
        logger.debug("Process level #{} (total users {})".format(step, level_counter))
        level_counter = len(level_queue)
        for user_index in range(level_counter):
            id = level_queue[user_index]
            total_users += 1
            settings.print_message("Process id {}. User #{} on level #{} (total {})".format(id, user_index, step, level_counter), 2)
            logger.debug("Process id {}. User #{} on level #{} (total {}).".format(id, user_index, step, level_counter))
            try:
                settings.print_message("Add user node in graph.", 3)
                logger.debug("Check user (id={}) in graph".format(id))
                if not id in graph.nodes.keys():
                    logger.debug("Create user node in graph (id={}).".format(id))
                    logger.debug("Get info for user (id={}).".format(id))
                    try:
                        user_info = api.users.get(user_ids=[id], fields = "photo_200_orig")
                    except Exception as error:
                        logger.warn(traceback.format_exc())
                        logger.debug("Can not get info for user (id={}), skip.".format(id))
                        settings.print_message("Can not get info for user, skip.", 3)
                        count_bad_users += 1
                        continue
                    if not user_info: 
                        logger.debug("Can not get info for user (id={}), skip.".format(id))
                        settings.print_message("Can not get info for user, skip.", 3)
                        count_bad_users += 1
                        continue
                    user_info = user_info[0]
                    logger.debug("User info='{}'.".format(json.dumps(user_info)))
                    logger.debug("Load user photo (id={}).".format(id))
                    photo = utils.get_request(user_info["photo_200_orig"])
                    if not photo:
                        logger.debug("Can't loading user photo (id={}).".format(id))
                    info_label = "ID: {} \nФИГ: {} {} \nНик: {} \nПол: {} \nДата рождения: {} \nГород: {} \nСтрана: {}".format(
                            id,
                            user_info["first_name"] if "first_name" in user_info else "----",
                            user_info["last_name"] if "last_name" in user_info else "----",
                            user_info["nickname"] if "nickname" in user_info else "----",
                            utils.SEX[user_info["sex"]] if "sex" in user_info else "----",
                            user_info["bdate"] if "bdate" in user_info else "----",
                            user_info["city"] if "city" in user_info else "----",
                            user_info["country"] if "country" in user_info else "----"
                                   )
                    graph.add_node(id, check_existance=False, label=info_label, shape="roundrectangle", font_style="italic", underlined_text="false", img=photo, width="200", height="200", border_has_color="false")
                    count_graph_users += 1
                else:
                    logger.debug("Graph contains user node (id={}).".format(id))
                    settings.print_message("Graph already contains this user node.", 3)
                settings.print_message("Get friendlist.", 3)
                logger.debug("Get friend for user (id={}).".format(id))
                try:
                    friends = api.friends.get(user_id=id, count=1000000, fields = "nickname, sex, bdate, city, country, photo_200_orig")
                except Exception as error:
                    logger.debug("Can not get friends, skip.")
                    settings.print_message("Can not get friendlist, skip.", 3)
                    count_bad_users += 1
                    continue
                if not friends:
                    logger.debug("Can not get friends, skip.")
                    settings.print_message("Can not get friendlist, skip.", 3)
                    count_bad_users += 1
                    continue
                settings.print_message("Process friends (total {}, level #{}).".format(len(friends), step + 1), 3)
                logger.debug("Friends count: {}".format(len(friends)))
                _ = [level_queue.append(friend["user_id"]) for friend in friends if not friend["user_id"] in graph.nodes]
                logger.debug("Add node for each friend and create edges.")
                for friend_index, friend in enumerate(friends):
                    total_users += 1
                    logger.debug("Process friend #{} (id={}).".format(friend_index, friend["user_id"]))
                    settings.print_message("Process friends #{} id={} (total {}, level #{}).".format(friend_index, friend["user_id"], len(friends), step + 1), 4)
                    #if friend_index > 10: break
                    settings.print_message("Add user node in graph.", 5)
                    logger.debug("Check user (id={}) in graph".format(friend["user_id"]))
                    if not friend["user_id"] in graph.nodes.keys():
                        logger.debug("Create user node in graph (id={}).".format(friend["user_id"]))
                        logger.debug("User info='{}'.".format(json.dumps(friend)))
                        logger.debug("Load user photo (id={}).".format(friend["user_id"]))
                        photo = utils.get_request(friend["photo_200_orig"])
                        if not photo:
                            logger.debug("Can't loading user photo (id={}).".format(friend["user_id"]))
                        info_label = "ID: {} \nФИГ: {} {} \nНик: {} \nПол: {} \nДата рождения: {} \nГород: {} \nСтрана: {}".format(
                            friend["user_id"],
                            friend["first_name"] if "first_name" in friend else "----",
                            friend["last_name"] if "last_name" in friend else "----",
                            friend["nickname"] if "nickname" in friend else "----",
                            utils.SEX[friend["sex"]] if "sex" in friend else "----",
                            friend["bdate"] if "bdate" in friend else "----",
                            friend["city"] if "city" in friend else "----",
                            friend["country"] if "country" in friend else "----"
                                   )
                        graph.add_node(friend["user_id"], check_existance=False, label=info_label, shape="roundrectangle", font_style="italic", underlined_text="false", img=photo, width="200", height="200", border_has_color="false")
                        count_graph_users += 1
                    else:
                        logger.debug("Graph contains user node (id={}).".format(friend["user_id"]))
                        settings.print_message("Graph already contains this user node.", 5)
                    logger.debug("Add adge {}-{} in graph.".format(friend["user_id"], id))
                    # if ...
                    graph.add_edge(friend["user_id"], id, width="1.0", color="#000000", check_existance_nodes=False)
            except Exception as error:
                logger.warn(traceback.format_exc())
                result = "with error"
        level_queue = level_queue[level_counter:]
    logger.debug("Create graphml for graph.")
    graph.construct_graphml()
    logger.debug("Save graphml in file {}.".format(settings.OUTPUT_FILE))
    try:
        with open(settings.OUTPUT_FILE, "w", encoding=settings.OUTPUT_ENCODING) as f:
            f.write(graph.get_graph())
    except Exception as error:
        logger.warn(traceback.format_exc())
        result = "with error"
    return (result, total_users, count_graph_users, count_bad_users)


def dispatch(command):
    result = None
    logger.debug("command %s.", command)
    start_time = datetime.now()
    try:
        for case in utils.Switch(command):
            if case("getFriendsGraph"): 
                logger.debug("Processing command '%s'." % command)
                settings.print_message("Processing command '%s'." % command)
                # START COMMAND
                result = get_friends_graph()
                logger.debug("Processing %s. Total users: %i. Users in graph: %i Bad requests: %i." % result)
                settings.print_message("Processing %s. Total users: %i. Users in graph: %i Bad requests: %i." % result)
                break
            if case(): # default
                logger.warn("Unknown command: %s" % command)
                settings.print_message("Unknown command: %s" % command)
                break
    except KeyboardInterrupt:
        settings.print_message("Caught KeyboardInterrupt, terminating processing")
    except:
        logger.error(traceback.format_exc())
        settings.print_message("Processing finished with error.")
        settings.print_message("For more details, see the log.")
    end_time = datetime.now()
    settings.print_message("Run began on {0}".format(start_time))
    settings.print_message("Run ended on {0}".format(end_time))
    settings.print_message("Elapsed time was: {0}".format(end_time - start_time))
    logger.debug("Run began on {0}".format(start_time))
    logger.debug("Run ended on {0}".format(end_time))
    logger.debug("Elapsed time was: {0}".format(end_time - start_time))


def main():  
    dispatch(settings.PARAMS["command"])


if __name__ == "__main__":
    main()