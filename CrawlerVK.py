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
import requests
import os
from base64 import b64encode
#
from pygraphml import Graph
import vk
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

    save_counter = settings.SAVE_COUNT

    result = "successful"

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
        level_counter = len(level_queue)
        settings.print_message("Process level #{} (total users {})".format(step, level_counter))
        logger.debug("Process level #{} (total users {})".format(step, level_counter))
        
        for user_index in range(level_counter):
            id = level_queue[user_index]
            total_users += 1
            save_counter -= 1
            if save_counter <= 0:
                save_counter = settings.SAVE_COUNT
                logger.debug("Create graphml for graph.")
                graph.construct_graphml()
                logger.debug("Save graphml in backup file backup_{}.".format(settings.OUTPUT_FILE))
                try:
                    with open("backup_{}".format(settings.OUTPUT_FILE), "w", encoding=settings.OUTPUT_ENCODING) as f:
                        f.write(graph.get_graph())
                except Exception as error:
                    logger.warn(traceback.format_exc())
                    logger.warn("Can not create backup file.")
            settings.print_message("Process id {}. User #{} on level #{} (total {})".format(id, user_index, step, level_counter), 2)
            logger.debug("Process id {}. User #{} on level #{} (total {}).".format(id, user_index, step, level_counter))
            try:
                settings.print_message("Add user node in graph.", 3)
                logger.debug("Check user (id={}) in graph".format(id))
                if not id in graph.nodes.keys():
                    logger.debug("Create user node in graph (id={}).".format(id))
                    logger.debug("Get info for user (id={}).".format(id))
                    try:
                        user_info = api.users.get(user_ids=[id],
                            fields = "nickname, sex, bdate, city, country, photo_200_orig, photo_200, photo_100")
                        if not user_info: raise Exception("User info is empty.")
                    except Exception as error:
                        logger.warn(traceback.format_exc())
                        logger.debug("Can not get info for user (id={}), skip.".format(id))
                        settings.print_message("Can not get info for user, skip.", 3)
                        count_bad_users += 1
                        continue
                    user_info = user_info[0]
                    logger.debug("User info='{}'.".format(json.dumps(user_info)))
                    logger.debug("Load user photo (id={}).".format(id))
                    photo = utils.get_request(user_info[settings.VK_PHOTO_1 if settings.VK_PHOTO_1 in user_info else settings.VK_PHOTO_2])
                    if not photo:
                        logger.debug("Can't loading user photo (id={}).".format(id))
                    info_label = "ФИГ: {} {} \nНик: {} \nID: {} \nПол: {} \nДата рождения: {} \nГород: {} \nСтрана: {}".format(
                            user_info["first_name"] if "first_name" in user_info else "----",
                            user_info["last_name"] if "last_name" in user_info else "----",
                            user_info["nickname"] if "nickname" in user_info else "----",
                            id,
                            utils.SEX[user_info["sex"]] if "sex" in user_info else "----",
                            user_info["bdate"] if "bdate" in user_info else "----",
                            user_info["city"] if "city" in user_info else "----",
                            user_info["country"] if "country" in user_info else "----"
                                   )
                    graph.add_node(id, check_existance=False, label=info_label, shape="roundrectangle", font_style="italic",
                        underlined_text="false", img=photo, width="200", height="200", border_has_color="false")
                    count_graph_users += 1
                else:
                    logger.debug("Graph contains user node (id={}).".format(id))
                    settings.print_message("Graph already contains this user node.", 3)
                settings.print_message("Get friendlist.", 3)
                logger.debug("Get friends for user (id={}).".format(id))
                try:
                    friends = api.friends.get(user_id=id, count=1000000, 
                        fields = "nickname, sex, bdate, city, country, photo_200_orig, photo_200, photo_100")
                    if not friends: raise Exception("User info is empty.")
                except Exception as error:
                    logger.warn(traceback.format_exc())
                    logger.debug("Can not get friends, skip.")
                    settings.print_message("Can not get friendlist, skip.", 3)
                    count_bad_users += 1
                    continue
                settings.print_message("Process friends (total {}, level #{}).".format(len(friends), step + 1), 3)
                logger.debug("Friends count: {}".format(len(friends)))
                _ = [level_queue.append(friend["user_id"]) for i, friend in enumerate(friends) 
                     if not friend["user_id"] in graph.nodes and i < settings.PARAMS["max_processing_friends"]]
                logger.debug("Add node for each friend and create edges.")
                for friend_index, friend in enumerate(friends):
                    total_users += 1
                    logger.debug("Process friend #{} (id={}).".format(friend_index, friend["user_id"]))
                    settings.print_message("Process friends #{} id={} (total {}, level #{}).".format(
                        friend_index, friend["user_id"], len(friends), step + 1), 4)
                    if friend_index > settings.PARAMS["max_processing_friends"]: break
                    settings.print_message("Add user node in graph.", 5)
                    logger.debug("Check user (id={}) in graph".format(friend["user_id"]))
                    if not friend["user_id"] in graph.nodes.keys():
                        logger.debug("Create user node in graph (id={}).".format(friend["user_id"]))
                        logger.debug("User info='{}'.".format(json.dumps(friend)))
                        logger.debug("Load user photo (id={}).".format(friend["user_id"]))
                        photo = utils.get_request(friend[settings.VK_PHOTO_1 if settings.VK_PHOTO_1 in friend else settings.VK_PHOTO_2])
                        if not photo:
                            logger.debug("Can't loading user photo (id={}).".format(friend["user_id"]))
                        info_label = "ФИГ: {} {} \nНик: {} \nID: {} \nПол: {} \nДата рождения: {} \nГород: {} \nСтрана: {}".format(
                            friend["first_name"] if "first_name" in friend else "----",
                            friend["last_name"] if "last_name" in friend else "----",
                            friend["nickname"] if "nickname" in friend else "----",
                            friend["user_id"],
                            utils.SEX[friend["sex"]] if "sex" in friend else "----",
                            friend["bdate"] if "bdate" in friend else "----",
                            friend["city"] if "city" in friend else "----",
                            friend["country"] if "country" in friend else "----"
                                   )
                        graph.add_node(friend["user_id"], check_existance=False, label=info_label, shape="roundrectangle",
                            font_style="italic", underlined_text="false", img=photo, width="200", height="200", border_has_color="false")
                        count_graph_users += 1
                    else:
                        logger.debug("Graph contains user node (id={}).".format(friend["user_id"]))
                        settings.print_message("Graph already contains this user node.", 5)
                    logger.debug("Add edge {}-{} in graph.".format(friend["user_id"], id))
                    # if ...
                    graph.add_edge(id, friend["user_id"], width="1.0", color="#000000", check_existance_nodes=False)
            except Exception as error:
                logger.warn(traceback.format_exc())
                result = "with error"
        level_queue = level_queue[level_counter:]
    logger.debug("Recovering the last level link.")
    settings.print_message("Recovering the last level link.")
    for user_index, user_id in enumerate(level_queue):
        settings.print_message("Process id {}. User #{} on last level (total {})".format(user_id, user_index, len(level_queue)), 2)
        settings.print_message("Get friendlist.", 2)
        logger.debug("Get friends for user (id={}).".format(user_id))
        loop_counter = settings.MAX_RETRY
        friends = None
        while(loop_counter > 0):
            try:
                loop_counter -= 1
                friends = api.friends.get(user_id=user_id, count=1000000)
                time.sleep(0.3)
                if not friends: raise utils.EmptyDataException("User info is empty.")
                break
            except vk.exceptions.VkAPIError as error:
                logger.warn(traceback.format_exc())
                if error.code == 6:
                    time.sleep(0.4)
                    continue
                else: break
            except utils.EmptyDataException as error:
                logger.warn(traceback.format_exc())
                break
            except Exception as error:
                logger.warn(traceback.format_exc())
                count_bad_users += 1
                loop_counter = settings.MAX_RETRY
                settings.print_message("Can not get friendlist, skip?", 2)
                if input("[y/n]: ") == 'n': continue
                logger.debug("Can not get friends, skip.")
                break
        if not friends: continue
        settings.print_message("Process friends (total {}).".format(len(friends)), 3)
        logger.debug("Friends count: {}".format(len(friends)))
        for friend_index, friend_id in enumerate(friends):
            if friend_id in graph.nodes.keys():
                logger.debug("Add edge {}-{} in graph.".format(friend_id, user_id))
                graph.add_edge(user_id, friend_id, width="1.0", color="#000000", check_existance_nodes=False)
    logger.debug("Create graphml for graph.")
    graph.construct_graphml()
    logger.debug("Save graphml in file {}.".format(settings.OUTPUT_FILE))
    try:
        with open(settings.OUTPUT_FILE, "w", encoding=settings.OUTPUT_ENCODING) as f:
            f.write(graph.get_graph())
        if os.path.exists("backup_{}".format(settings.OUTPUT_FILE)): os.remove("backup_{}".format(settings.OUTPUT_FILE))
    except Exception as error:
        logger.warn(traceback.format_exc())
        result = "with error"
    return (result, total_users, count_graph_users, count_bad_users)


def get_friends_of_users(uids):
    """ Get lists of friends by users with uid of uids and create social graph  """
    total_users = 0
    count_bad_users = 0
    count_graph_users = 0

    save_counter = settings.SAVE_COUNT

    result = "successful"

    settings.print_message("Create VK session for application (app_id={})".format(settings.VK_APPLICATION_ID))
    logger.debug("Create VK session for application (app_id={}).".format(settings.VK_APPLICATION_ID))
    try:
        session = vk.Session(access_token=settings.VK_ACCESS_TOKEN)
        api = vk.API(session)
    except Exception as error:
        logger.warn(traceback.format_exc())
        settings.print_message("Can't create VK session for application with app_id={}".format(settings.VK_APPLICATION_ID))
        return ("with error.", 0, 0, 0)
    graph = yEdGraph.Graph()

    for user_index, id in enumerate(uids):
        total_users += 1
        save_counter -= 1
        if save_counter <= 0:
            save_counter = settings.SAVE_COUNT
            logger.debug("Create graphml for graph.")
            graph.construct_graphml()
            logger.debug("Save graphml in backup file backup_{}.".format(settings.OUTPUT_FILE))
            try:
                with open("backup_{}".format(settings.OUTPUT_FILE), "w", encoding=settings.OUTPUT_ENCODING) as f:
                    f.write(graph.get_graph())
            except Exception as error:
                logger.warn(traceback.format_exc())
                logger.warn("Can not create backup file.")
        settings.print_message("Process id {}. User #{} (total {})".format(id, user_index, len(uids)), 2)
        logger.debug("Process id {}. User #{} (total {})".format(id, user_index, len(uids)))
        try:
            settings.print_message("Add user node in graph.", 3)
            logger.debug("Check user (id={}) in graph".format(id))
            if not id in graph.nodes.keys():
                logger.debug("Create user node in graph (id={}).".format(id))
                logger.debug("Get info for user (id={}).".format(id))
                try:
                    user_info = api.users.get(user_ids=[id],
                        fields = "nickname, sex, bdate, city, country, photo_200_orig, photo_200, photo_100")
                    if not user_info: raise Exception("User info is empty.")
                except Exception as error:
                    logger.warn(traceback.format_exc())
                    logger.debug("Can not get info for user (id={}), skip.".format(id))
                    settings.print_message("Can not get info for user, skip.", 3)
                    count_bad_users += 1
                    continue
                user_info = user_info[0]
                id = user_info["uid"]
                logger.debug("User info='{}'.".format(json.dumps(user_info)))
                logger.debug("Load user photo (id={}).".format(id))
                photo = utils.get_request(user_info[settings.VK_PHOTO_1 if settings.VK_PHOTO_1 in user_info else settings.VK_PHOTO_2])
                if not photo:
                    logger.debug("Can't loading user photo (id={}).".format(id))
                info_label = "ФИГ: {} {} \nНик: {} \nID: {} \nПол: {} \nДата рождения: {} \nГород: {} \nСтрана: {}".format(
                        user_info["first_name"] if "first_name" in user_info else "----",
                        user_info["last_name"] if "last_name" in user_info else "----",
                        user_info["nickname"] if "nickname" in user_info else "----",
                        id,
                        utils.SEX[user_info["sex"]] if "sex" in user_info else "----",
                        user_info["bdate"] if "bdate" in user_info else "----",
                        user_info["city"] if "city" in user_info else "----",
                        user_info["country"] if "country" in user_info else "----"
                               )
                graph.add_node(id, check_existance=False, label=info_label, shape="roundrectangle", font_style="italic",
                    underlined_text="false", img=photo, width="200", height="200", border_has_color="false")
                count_graph_users += 1
            else:
                logger.debug("Graph contains user node (id={}).".format(id))
                settings.print_message("Graph already contains this user node.", 3)
            settings.print_message("Get friendlist.", 3)
            logger.debug("Get friends for user (id={}).".format(id))
            try:
                friends = api.friends.get(user_id=id, count=1000000, 
                    fields = "nickname, sex, bdate, city, country, photo_200_orig, photo_200, photo_100")
                if not friends: raise Exception("User info is empty.")
            except Exception as error:
                logger.warn(traceback.format_exc())
                logger.debug("Can not get friends, skip.")
                settings.print_message("Can not get friendlist, skip.", 3)
                count_bad_users += 1
                continue
            settings.print_message("Process friends (total {}).".format(len(friends)), 3)
            logger.debug("Friends count: {}".format(len(friends)))
            logger.debug("Add node for each friend and create edges.")
            for friend_index, friend in enumerate(friends):
                total_users += 1
                logger.debug("Process friend #{} (id={}).".format(friend_index, friend["user_id"]))
                settings.print_message("Process friends #{} id={} (total {}).".format(
                    friend_index, friend["user_id"], len(friends)), 4)
                if friend_index > settings.PARAMS["max_processing_friends"]: break
                settings.print_message("Add user node in graph.", 5)
                logger.debug("Check user (id={}) in graph".format(friend["user_id"]))
                if not friend["user_id"] in graph.nodes.keys():
                    logger.debug("Create user node in graph (id={}).".format(friend["user_id"]))
                    logger.debug("User info='{}'.".format(json.dumps(friend)))
                    logger.debug("Load user photo (id={}).".format(friend["user_id"]))
                    photo = utils.get_request(friend[settings.VK_PHOTO_1 if settings.VK_PHOTO_1 in friend else settings.VK_PHOTO_2])
                    if not photo:
                        logger.debug("Can't loading user photo (id={}).".format(friend["user_id"]))
                    info_label = "ФИГ: {} {} \nНик: {} \nID: {} \nПол: {} \nДата рождения: {} \nГород: {} \nСтрана: {}".format(
                        friend["first_name"] if "first_name" in friend else "----",
                        friend["last_name"] if "last_name" in friend else "----",
                        friend["nickname"] if "nickname" in friend else "----",
                        friend["user_id"],
                        utils.SEX[friend["sex"]] if "sex" in friend else "----",
                        friend["bdate"] if "bdate" in friend else "----",
                        friend["city"] if "city" in friend else "----",
                        friend["country"] if "country" in friend else "----"
                               )
                    graph.add_node(friend["user_id"], check_existance=False, label=info_label, shape="roundrectangle",
                        font_style="italic", underlined_text="false", img=photo, width="200", height="200", border_has_color="false")
                    count_graph_users += 1
                else:
                    logger.debug("Graph contains user node (id={}).".format(friend["user_id"]))
                    settings.print_message("Graph already contains this user node.", 5)
                logger.debug("Add edge {}-{} in graph.".format(friend["user_id"], id))
                # if ...
                graph.add_edge(id, friend["user_id"], width="1.0", color="#000000", check_existance_nodes=False)
        except Exception as error:
            logger.warn(traceback.format_exc())
            result = "with error"
    logger.debug("Create graphml for graph.")
    graph.construct_graphml()
    logger.debug("Save graphml in file {}.".format(settings.OUTPUT_FILE))
    try:
        with open(settings.OUTPUT_FILE, "w", encoding=settings.OUTPUT_ENCODING) as f:
            f.write(graph.get_graph())
        if os.path.exists("backup_{}".format(settings.OUTPUT_FILE)): os.remove("backup_{}".format(settings.OUTPUT_FILE))
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
            if case("getFriendsByUIDs"): 
                logger.debug("Processing command '%s'." % command)
                settings.print_message("Processing command '%s'." % command)
                # START COMMAND
                result = get_friends_of_users(settings.PARAMS["user_ids"])
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