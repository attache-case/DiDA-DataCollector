# coding: utf-8

## imports

from pymongo import MongoClient
import ipywidgets as widgets

import multiprocessing as multi
from multiprocessing import Pool
from multiprocessing import Process

import sys
import json
import math
import time
from datetime import datetime
import urllib.request
from collections import deque

import pandas as pd
import subprocess

import re
import random

import env
import dbg



## initialize token queue
token_q = deque([])
dbg.log("", "using these tokens...")
for item in env.personal_access_token_list:
    token_q.append(item["token"])
    dbg.log("", "  " + item["token"])



#############
# functions #
#############

## Access GraphQL API


def accessGitHubAPI(_query, _token):

    url = "https://api.github.com/graphql"
    method = "POST"
    headers = {"Authorization": "bearer " + _token}
    obj = {"query": _query}
    json_data = json.dumps(obj).encode("utf-8")
    request = urllib.request.Request(
        url, data=json_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request) as response:
            response_body = response.read().decode("utf-8")
            result_obj = json.loads(response_body)
        return result_obj
    except:
        dbg.log("API/ERR", sys.exc_info()[0].__name__)
        raise


## queue management


def getTokenFromQueue():
    global token_q
    return token_q.popleft()


def putBackToken(_token):
    global token_q
    token_q.appendleft(_token)


def restCurrentToken(_current_token):
    global token_q
    token_q.append(_current_token)


## dictionary key checker


def check_key(d, key1, key2="", key3=""):

    if key1 in d:
        if key2 is "":
            return True
        elif d[key1] is not None and key2 in d[key1]:
            if key3 is "":
                return True
            elif d[key1][key2] is not None and key3 in d[key1][key2]:
                return True
    return False


## write scraped data to DB

def ids2string(IDs):
    s = ''
    for i, ID in enumerate(IDs):
        if i == 0:
            s = '"' + ID + '"'
        else:
            s = s + ', "' + ID + '"'
    return s



def subquery_DBupdate(mongo_client, collection, repo, subquery_target, ID, edges):

    db = mongo_client[env.db_name]
    db_issues = db[env.col_issues]
    db_pulls = db[env.col_pulls]
    db_commits = db[env.col_commits]

    array = []
    
    if subquery_target == "labels":
        for node_root in edges:
            array.append(node_root["node"]["name"])

    elif subquery_target == "comments":
        for node_root in edges:
            node = node_root["node"]
            if node is None or check_key(node, "id") is False:
                continue
            comment = dict(
                ID=node["id"],
                body=node["body"],
                createdAt=node["createdAt"],
                lastEditedAt=node["lastEditedAt"]
            )
            if check_key(node, "author", "login") is True:
                comment["author_login"] = node["author"]["login"]
                comment["authorAssociation"] = node["authorAssociation"]
            array.append(comment)
    
    elif subquery_target == "reactions":
        for node_root in edges:
            node = node_root["node"]
            if node is None or check_key(node, "id") is False:
                continue
            reaction = dict(
                ID=node["id"],
                content=node["content"],
                createdAt=node["createdAt"])
            if check_key(node, "user", "login") is True:
                reaction["user_login"] = node["user"]["login"]
            array.append(reaction)
    
    elif subquery_target == "reviews":
        for node_root in edges:
            node = node_root["node"]
            if node is None or check_key(node, "id") is False:
                continue
            review = dict(
                ID=node["id"],
                body=node["body"],
                state=node["state"],
                createdAt=node["createdAt"],
                lastEditedAt=node["lastEditedAt"])
            if check_key(node, "author", "login") is True:
                review["author_login"] = node["author"]["login"]
            if check_key(node, "commit", "id") is True:
                review["commit_id"] = node["commit"]["id"]
            array.append(review)
    
    elif subquery_target == "commits":
        for node_root in edges:
            node = node_root["node"]
            if node is None or check_key(node, "commit") is False:
                continue
            commit = node["commit"]
            if commit is None or check_key(commit, "id") is False:
                continue
            array.append(commit["id"])
            record_commit = dict(
                ID=commit["id"],
                oid=commit["oid"],
                repo_id=commit["repository"]["id"],
                message=commit["message"],
                messageBody=commit["messageBody"],
                committedDate=commit["committedDate"],
                pushedDate=commit["pushedDate"],
            )
            if check_key(commit, "author", "user", "login") is True:
                record_commit["author_login"] = commit["author"]["user"]["login"]
            if check_key(commit, "committer", "user", "login") is True:
                record_commit["committer_login"] = commit["committer"]["user"]["login"]
            record_commit["refFrom" + "PullRequest"] = ID
            try:
                db_commits.update_one(
                    {
                        'ID': record_commit["ID"]
                    }, {'$set': record_commit},
                    upsert=True)
            except:
                dbg.log("UPDATE/SKIP", record_commit["ID"])
    
    elif subquery_target == "timeline":
        for node_root in edges:
            node = node_root["node"]
            if node is None:
                continue
            timeline = dict(TYPE=node["__typename"])
            if timeline["TYPE"] == "Commit":
                if node is None or check_key(node, "id") is False:
                    continue
                timeline["ID"] = node["id"]
                if check_key(node, "oid") is False:
                    # oid is NOT collected on the context of PullRequest
                    # detail of Commit in PullRequest is collected in Commits (NOT timeline)
                    array.append(timeline)
                    continue
                record_commit = dict(
                    ID=node["id"],
                    oid=node["oid"],
                    repo_id=node["repository"]["id"],
                    message=node["message"],
                    messageBody=node["messageBody"],
                    committedDate=node["committedDate"],
                    pushedDate=node["pushedDate"]
                )
                if check_key(node, "author", "user", "login") is True:
                    record_commit["author_login"] = node["author"]["user"]["login"]
                if check_key(node, "committer", "user", "login") is True:
                    record_commit["committer_login"] = node["committer"]["user"]["login"]
                record_commit["refFrom" + "Issue"] = ID
                try:
                    db_commits.update_one(
                        {
                            'ID': record_commit["ID"]
                        }, {'$set': record_commit},
                        upsert=True)
                except:
                    dbg.log("UPDATE/SKIP", record_commit["ID"])
            elif timeline["TYPE"] == "IssueComment":
                if node is None or check_key(node, "id") is False:
                    continue
                timeline["ID"] = node["id"]
            elif timeline["TYPE"] == "CrossReferencedEvent":
                if node is None or check_key(node, "id") is False:
                    continue
                crossReference = dict(
                    ID=node["id"],
                    isCrossRepository=node["isCrossRepository"],
                    referencedAt=node["referencedAt"],
                )
                if check_key(node, "source", "id") is False:
                    continue
                source = dict(
                    TYPE=node["source"]["__typename"],
                    ID=node["source"]["id"],
                    number=node["source"]["number"])
                if check_key(node, "target" ,"id") is False:
                    continue
                target = dict(
                    TYPE=node["target"]["__typename"],
                    ID=node["target"]["id"],
                    number=node["target"]["number"]
                )
                crossReference["source"] = source
                crossReference["target"] = target
                referred_to = {"refTo" + crossReference["target"]["TYPE"]: crossReference["target"]["ID"]}
                referred_from = {
                    "refFrom" + crossReference["source"]["TYPE"]:
                    crossReference["source"]["ID"]
                }
                try:
                    if crossReference["target"]["TYPE"] == "Issue":
                        db_issues.update_one(
                            {
                                'ID': crossReference["target"]["ID"]
                            }, {'$addToSet': referred_from},
                            upsert=True)
                    elif crossReference["target"]["TYPE"] == "PullRequest":
                        db_pulls.update_one(
                            {
                                'ID': crossReference["target"]["ID"]
                            }, {'$addToSet': referred_from},
                            upsert=True)
                except:
                    dbg.log("UPDATE/SKIP", ID)
                try:
                    if crossReference["source"]["TYPE"] == "Issue":
                        db_issues.update_one(
                            {
                                'ID': crossReference["source"]["ID"]
                            }, {'$addToSet': referred_to},
                            upsert=True)
                    elif crossReference["source"]["TYPE"] == "PullRequest":
                        db_pulls.update_one(
                            {
                                'ID': crossReference["source"]["ID"]
                            }, {'$addToSet': referred_to},
                            upsert=True)
                except:
                    dbg.log("UPDATE/SKIP", crossReference["source"]["ID"])
                timeline.update(crossReference)
            else:
                if check_key(node, "createdAt") is True:
                    timeline["createdAt"] = node["createdAt"]
            array.append(timeline)
    
    try:
        collection.update_one({"ID":ID},{"$push": { subquery_target: { "$each": array } }})
    except KeyboardInterrupt as e:
        raise
    except:
        repo_name = repo["repo_name"]
        repo_owner_name = repo["owner"]
        if sys.exc_info()[0].__name__ == 'OperationFailure':
            dbg.log("UPDATE/OFERR", ID,
                        repo_owner_name + "/" + repo_name)
        elif sys.exc_info()[0].__name__ == 'WriteError':
            dbg.log("UPDATE/WERR", ID,
                        repo_owner_name + "/" + repo_name)
        elif sys.exc_info()[0].__name__ == 'DocumentTooLarge':
            dbg.log("UPDATE/LERR", ID,
                        repo_owner_name + "/" + repo_name)
        else:
            raise

def subquery_main(mongo_client, collection, query_master, IDs, str_filter, repo, subquery_key):
    global token_q

    remainingIDs = []
    remainingCursors = []
    
    params = dict(str_ids=ids2string(IDs), filter=str_filter)

    query = query_master % params

    retry = 0

    while True:
        token = getTokenFromQueue()
        try:
            result = accessGitHubAPI(query, token)
            break
        except KeyboardInterrupt as e:
            raise
        except:
            retry += 1
            putBackToken(token)
            if retry < env.MAX_RETRY:
                dbg.log("API/RETRY", str(retry))
                time.sleep(random.randint(1,5))
                continue
            else:
                dbg.log("API/GIVEUP")
                break

    try:
        data = result['data']['nodes']
    except:
        dbg.log("ILLDATA")
        putBackToken(token)
        return dict(IDs=[], Cursors=[])

    # token management
    if result['data']['rateLimit']['remaining'] < env.LIMIT_CUTOFF:
        restCurrentToken(token)
        dbg.log("TOK/REST", token)
    else:
        putBackToken(token)
    
    for node in data:
        subquery_data = node[env.subquery_target[subquery_key]]
        if subquery_data["edges"] != []:
            pageInfo = subquery_data['pageInfo']
            hasNextPage = pageInfo['hasNextPage']
            nextCursor = pageInfo['endCursor']
            if hasNextPage:
                remainingIDs.append(node["id"])
                remainingCursors.append(nextCursor)
            subquery_DBupdate(mongo_client, collection, repo, env.subquery_target[subquery_key], node["id"], subquery_data["edges"])

    return dict(IDs=remainingIDs, Cursors=remainingCursors)



def process_subquery(mongo_client, collection, target, IDs, repo, subquery_key):

    if target == "Issue":
        query_master = env.subquery_issue_master
    elif target == "PullRequest":
        query_master = env.subquery_pull_master

    # embedding params to the query (must be this order to embed)
    query_master = query_master.replace("%("+"subquery"+")s", env.subquery[subquery_key])
    query_master = query_master.replace("%("+"pageInfo"+")s", env.subquery["pageInfo"])

    remaining = subquery_main(mongo_client, collection, query_master, IDs, "", repo, subquery_key)

    while len(remaining["IDs"])!=0:
        dbg.log("MORE", subquery_key, str(len(remaining["IDs"])))
        remaining_new = dict(IDs=[], Cursors=[])
        for (ID, Cursor) in zip(remaining["IDs"], remaining["Cursors"]):
            filter_string = 'after:"' + Cursor + '"'
            result = subquery_main(mongo_client, collection, query_master, [ID], filter_string, repo, subquery_key)
            if len(result["IDs"])==0:
                pass
            else:
                remaining_new["IDs"].append(result["IDs"][0])
                remaining_new["Cursors"].append(result["Cursors"][0])
        remaining = remaining_new



def update_collection(collection, ID, record, repo):
    
    try:
        collection.update_one(
            {
                'ID': ID
            }, {'$set': record},
            upsert=True)
    except KeyboardInterrupt as e:
        raise
    except:
        repo_name = repo["repo_name"]
        repo_owner_name = repo["owner"]
        if sys.exc_info()[0].__name__ == 'OperationFailure':
            dbg.log("UPDATE/OFERR", ID,
                        repo_owner_name + "/" + repo_name)
        elif sys.exc_info()[0].__name__ == 'WriteError':
            dbg.log("UPDATE/WERR", ID,
                        repo_owner_name + "/" + repo_name)
        elif sys.exc_info()[0].__name__ == 'DocumentTooLarge':
            dbg.log("UPDATE/LERR", ID,
                        repo_owner_name + "/" + repo_name)
        else:
            raise

def update_DB_with_issue_data(mongo_client, data, repo):
    
    db = mongo_client[env.db_name]

    db_issues = db[env.col_issues]

    IDs = []

    for node_root in data:
        node = node_root["node"]
        if node is None or check_key(node, "id") is False:
            continue
        # update issue record
        record_issue = dict(
            ID=node["id"],
            repo_id=node["repository"]["id"],
            number=node["number"],
            title=node["title"],
            body=node["body"],
            createdAt=node["createdAt"],
            lastEditedAt=node["lastEditedAt"],
            state=node["state"],
            labels=[],
            comments=[],
            timeline=[],
            reactions=[])
        if check_key(node, "author", "login") is True:
            record_issue["author_login"] = node["author"]["login"]
            record_issue["authorAssociation"] = node["authorAssociation"]

        update_collection(db_issues, record_issue["ID"], record_issue, repo)
        IDs.append(record_issue["ID"])
    
    for subquery_key in env.subquery_keys["issue"]:
        process_subquery(mongo_client, db_issues, "Issue", IDs, repo, subquery_key)
    


def update_DB_with_pull_data(mongo_client, data, repo):
    
    db = mongo_client[env.db_name]

    db_pulls = db[env.col_pulls]
    
    IDs = []

    for node_root in data:
        node = node_root["node"]
        if node is None or check_key(node, "id") is False:
            continue
        # update pull request record
        record_pull = dict(
            ID=node["id"],
            repo_id=node["repository"]["id"],
            number=node["number"],
            title=node["title"],
            body=node["body"],
            mergedAt=node["mergedAt"],
            createdAt=node["createdAt"],
            lastEditedAt=node["lastEditedAt"],
            state=node["state"],
            additions=node["additions"],
            deletions=node["deletions"],
            changedFiles=node["changedFiles"],
            labels=[],
            commits=[],
            comments=[],
            reviews=[],
            timeline=[],
            reactions=[])
        if check_key(node, "author", "login") is True:
            record_pull["author_login"] = node["author"]["login"]
            record_pull["authorAssociation"] = node["authorAssociation"]

        update_collection(db_pulls, record_pull["ID"], record_pull, repo)
        IDs.append(record_pull["ID"])

    for subquery_key in env.subquery_keys["pull"]:
        process_subquery(mongo_client, db_pulls, "PullRequest", IDs, repo, subquery_key)



def updateDB(mongo_client, data, repo, _scrape_target_string):

    if _scrape_target_string == env.str_target_issue:
        update_DB_with_issue_data(mongo_client, data, repo)
    elif _scrape_target_string == env.str_target_pull:
        update_DB_with_pull_data(mongo_client, data, repo)


## scraping


def scrape(mongo_client, repo, _scrape_target_string):
    global token_q

    repo_name = repo["repo_name"]
    repo_owner_name = repo["owner"]

    db = mongo_client[env.db_name]
    db_repos = db[env.col_repos]

    # to scrape all components
    hasNextPage = True
    nextCursor = ""
    filter_string = ""

    # field strings used to update scraping flag state
    str_flag = _scrape_target_string + "_scraped_flag"
    str_suspended = _scrape_target_string + "_scrape_suspended"
    str_cursor_key = _scrape_target_string + "_nextCursor"

    # skip or resume according to scraping flag state
    if repo.get(str_flag) is not None:
        if repo[str_flag] is True:
            dbg.log("", _scrape_target_string+" already scraped")
            return True
        else:
            if repo.get(
                    str_suspended) is not None and repo[str_suspended] is True:
                nextCursor = repo[str_cursor_key]
    
    params = dict(repo_owner_name=repo_owner_name, repo_name=repo_name, pageInfo=env.subquery["pageInfo"])

    if _scrape_target_string == env.str_target_issue:
        query_master = env.query_issue_master
        number_of_scraping = env.number_of_scraping_issues
        params["number_of_scraping_issues"] = "%(" + "number_of_scraping" + ")s"
    elif _scrape_target_string == env.str_target_pull:
        query_master = env.query_pull_master
        number_of_scraping = env.number_of_scraping_pulls
        params["number_of_scraping_pulls"] = "%(" + "number_of_scraping" + ")s"
    else:
        dbg.log("TARGET/ERR", _scrape_target_string)
        return False

    # embedding params to the query
    for key in params.keys():
        query_master = query_master.replace("%("+key+")s", str(params[key]))

    loop_successful = False
    retry = 0
    number_of_scraping_normal = number_of_scraping

    while (hasNextPage):

        # if this while loop finishes without any "break", loop_successful will be True
        loop_successful = False

        # set cursor
        if nextCursor != "":
            filter_string = 'after:"' + nextCursor + '"'

        query = query_master % dict(number_of_scraping=number_of_scraping, filter=filter_string) # embedding filters to the query

        token = getTokenFromQueue()

        try:
            result = accessGitHubAPI(query, token)
            retry = 0
            # reset number of scraping to normal(50) when API access success
            number_of_scraping = number_of_scraping_normal
        except KeyboardInterrupt as e:
            raise
        except:
            retry += 1
            # lessen number of scraping temporary when API access fails
            number_of_scraping = 1
            putBackToken(token)
            if retry < env.MAX_RETRY:
                dbg.log("API/RETRY", str(retry))
                time.sleep(random.randint(1,5))
                continue
            else:
                dbg.log("API/GIVEUP")
                break

        try:
            data = result['data']['repository'][
                _scrape_target_string]['edges']
        except:
            dbg.log("ILLDATA")
            putBackToken(token)
            break

        # token management
        if result['data']['rateLimit']['remaining'] < env.LIMIT_CUTOFF:
            restCurrentToken(token)
            dbg.log("TOK/REST", token)
        else:
            putBackToken(token)

        try:
            updateDB(mongo_client, data, repo, _scrape_target_string)
        except KeyboardInterrupt as e:
            raise
        except:
            if sys.exc_info()[0].__name__ == 'OperationFailure':
                dbg.log("UPDATE/BATCH/OFERR", nextCursor, repo_owner_name+"/"+repo_name)
                pass
            elif sys.exc_info()[0].__name__ == 'TooManyRequests':
                dbg.log("UPDATE/BATCH/RQERR", nextCursor, repo_owner_name+"/"+repo_name)
                time.sleep(5)
                pass
            elif sys.exc_info()[0].__name__ == 'ExecutionTimeout':
                dbg.log("UPDATE/BATCH/TOERR", nextCursor, repo_owner_name+"/"+repo_name)
                pass
            else:
                raise

        pageInfo = result['data']['repository'][_scrape_target_string][
            'pageInfo']
        hasNextPage = pageInfo['hasNextPage']
        nextCursor = pageInfo['endCursor']

        # update scraping state
        db_repos.update_one(
            {
                'ID': repo["ID"]
            }, {
                '$set': {
                    str_flag: False,
                    str_suspended: True,
                    str_cursor_key: nextCursor
                }
            },
            upsert=False)

        # if this while loop finishes without any "break", loop_successful will be True
        loop_successful = True

    if loop_successful == True:
        db_repos.update_one(
            {
                'ID': repo["ID"]
            }, {'$set': {
                str_flag: True,
                str_suspended: False,
                str_cursor_key: nextCursor
            }},
            upsert=False)
    else:
        db_repos.update_one(
            {
                'ID': repo["ID"]
            }, {
                '$set': {
                    str_flag: False,
                    str_suspended: True,
                    str_cursor_key: nextCursor
                }
            },
            upsert=False)

    if loop_successful == True:
        return True
    else:
        return False



## write diff data


def diff_writer(mongo_client, repo):

    repo_name = repo["repo_name"]
    repo_owner_name = repo["owner"]

    # field strings used to update scraping flag state
    str_flag = "diff" + "_scraped_flag"
    str_suspended = "diff" + "_scrape_suspended"
    str_cursor_key = "diff" + "_Cursor"
    Cursor = 0

    # skip or resume according to scraping flag state
    if repo.get(str_flag) is not None:
        if repo[str_flag] is True:
            dbg.log("", "diff"+" already scraped")
            return True
        else:
            if repo.get(
                    str_suspended) is not None and repo[str_suspended] is True:
                Cursor = repo[str_cursor_key]
    
    db = mongo_client[env.db_name]
    db_commits = db[env.col_commits]
    db_repos = db[env.col_repos]

    df_commits = pd.DataFrame(
        list(db[env.col_commits].find({
            "repo_id": repo["ID"]
        }, {
            "ID": 1,
            "oid": 1,
            "_id": 0
        })))
    
    # skip if the Repository does not have PullRequests as well as Commits
    if len(df_commits) == 0:
        dbg.log("", "No commits to process: " + repo_owner_name + "/" + repo_name)
        return False

    # check "repos" directory exists
    output = subprocess.check_output(
        "test -d ./repos && echo '1' || echo '0'",
        shell=True).decode('utf-8').replace('\n', '')
    if output == '0':
        dbg.log("", "No 'repos' directory. Creating 'repos' directory...")
        output = subprocess.check_output(
            "mkdir repos && echo '1' || echo '0'",
            shell=True).decode('utf-8').replace('\n', '')
        dbg.log("", 'Success' if output == '1' else 'Failed')
    # check if repository already cloned
    dbg.log("", "find " + repo_name + " directory...")
    output = subprocess.check_output(
        "test -d ./repos/" + repo_name + " && echo '1' || echo '0'",
        shell=True).decode('utf-8').replace('\n', '')
    dbg.log("", 'Success' if output == '1' else 'Failed')
    if output == '0':
        # clone repository
        dbg.log("", "cloning https://github.com/" + repo_owner_name + "/" +
                     repo_name + ".git ...")
        output = subprocess.check_output(
            "git -C ./repos clone https://github.com/" + repo_owner_name +
            "/" + repo_name + ".git" + " && echo '1' || echo '0'",
            shell=True).decode('utf-8').replace('\n', '')
        dbg.log("", 'Success' if output == '1' else 'Failed')
        if output == '0':
            dbg.log("", "Failed to clone" + repo_owner_name + "/" + reponame)
            return False
        dbg.log("", "checking " + repo_name + " directory...")
        output = subprocess.check_output(
            "test -d ./repos/" + repo_name + " && echo '1' || echo '0'",
            shell=True).decode('utf-8').replace('\n', '')
        dbg.log("", 'Success' if output == '1' else 'Failed')

    dbg.log("", "cloned and start scraipng diffs: " + repo_owner_name + "/" + repo_name)

    # write diff phase

    # resume operation
    resume_index = 0

    if Cursor != 0:
        resume_index = Cursor

    str_HEAD = "diff --git"

    loop_successful = False

    CPError_count = 0
    CPEroor_IDs = []

    for index, commit in df_commits.iterrows():
        if index < resume_index:
            continue
        loop_successful = False
        oid = commit['oid']
        Cursor = index
        try:
            diff = subprocess.check_output(
                "git -C ./repos/" + repo_name +
                " diff -U0 -w --ignore-blank-lines --find-renames " + oid +
                "^.." + oid,
                shell=True).decode('utf-8')
            diff_list = diff.split(str_HEAD)
            fileChanges_list = []
            for k, d in enumerate(diff_list):
                if d == "":
                    pass
                else:
                    d = str_HEAD + d
                    paths = re.findall(r"diff --git a/(\S+) b/(\S+)\n", d)
                    if paths != []:
                        paths = paths[0]
                    else:
                        paths = ['undefined', 'undefined']
                    fileChanges = dict(
                        diffBody=d,
                        additions=len(re.findall(r"\n\+[^+]", d)),
                        deletions=len(re.findall(r"\n-[^-]", d)),
                        path_before=paths[0],
                        path_after=paths[1])
                    fileChanges_list.append(fileChanges)
                    if len(fileChanges["diffBody"]) > 10000:
                        time.sleep(0.002*(len(fileChanges["diffBody"])//10000))
            db_commits.update_one(
                {
                    'ID': commit["ID"]
                }, {'$set': {
                    "fileChanges": fileChanges_list
                }},
                upsert=True)
        except KeyboardInterrupt as e:
            db_repos.update_one(
                {
                    'ID': repo["ID"]
                }, {
                    '$set': {
                        str_flag: False,
                        str_suspended: True,
                        str_cursor_key: Cursor
                    }
                },
                upsert=False)
            mongo_client.close()
        except subprocess.CalledProcessError as e:
            CPError_count += 1
            CPEroor_IDs.append(commit["ID"])
            # dbg.log("DIFF-COMMIT/ERR", index, oid)
        except UnicodeDecodeError as e:
            dbg.log("DIFF-COMMIT/UCERR", index, oid)
        except:
            if sys.exc_info()[0].__name__ == 'OperationFailure':
                dbg.log("DIFF-COMMIT/OFERR", index, oid)
            elif sys.exc_info()[0].__name__ == 'WriteError':
                dbg.log("DIFF-COMMIT/WERR", index, oid)
            elif sys.exc_info()[0].__name__ == 'DocumentTooLarge':
                dbg.log("DIFF-COMMIT/LERR", index, oid)
            else:
                db_repos.update_one(
                    {
                        'ID': repo["ID"]
                    }, {
                        '$set': {
                            str_flag: False,
                            str_suspended: True,
                            str_cursor_key: Cursor
                        }
                    },
                    upsert=False)
                raise
        loop_successful = True

    dbg.log("", str(CPError_count)+" CPErrors")
    print(repo_owner_name,repo_name,CPEroor_IDs)

    dbg.log("", "finished writing diffs")

    # delete directory after writing diffs
    dbg.log("", "deleting " + repo_name + " directory...")
    output = subprocess.check_output(
        "rm -r ./repos/" + repo_name + " && echo '1' || echo '0'",
        shell=True).decode('utf-8').replace('\n', '')
    dbg.log("", 'Success' if output == '1' else 'Failed')

    if loop_successful == True:
        db_repos.update_one(
            {
                'ID': repo["ID"]
            }, {
                '$set': {
                    str_flag: True,
                    str_suspended: False,
                    str_cursor_key: Cursor
                }
            },
            upsert=False)
    else:
        db_repos.update_one(
            {
                'ID': repo["ID"]
            }, {
                '$set': {
                    str_flag: False,
                    str_suspended: True,
                    str_cursor_key: Cursor
                }
            },
            upsert=False)

    if loop_successful == True:
        return True
    else:
        return False