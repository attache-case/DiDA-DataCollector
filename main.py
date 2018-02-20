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
import requests

import pandas as pd
import subprocess

import re

import env
import scraping
import dbg

## main process of scraping

def send_slack_notification(s):
  URL = 'WRITE_YOUR_SLACK_WEBHOOK_URL'
  TEXT = s
  USERNAME = 'Data Collect Notifier'

  post_json = {
    'text': TEXT,
    'username': USERNAME,
    'link_names': 1
  }
  requests.post(URL, data = json.dumps(post_json))

def process(repo):

  mongo_client = MongoClient(env.mongo_uri)

  dbg.log("", "process assigned")

  db = mongo_client[env.db_name]
  db_repos = db[env.col_repos]

  repo_name = repo["repo_name"]
  repo_owner_name = repo["owner"]

  dbg.log("", "Repository: " + repo_owner_name + "/" + repo_name)

  # scrape issues
  scrape_issues_success = scraping.scrape(mongo_client, repo, env.str_target_issue)

  # scrape pull requests
  scrape_pulls_success = scraping.scrape(mongo_client, repo, env.str_target_pull)

  dbg.log(
    "", "scraping  result(" + repo_owner_name + "/" + repo_name + "): ISSUE->"
    + str(scrape_issues_success) + ", PULL->" + str(scrape_pulls_success))
  if scrape_issues_success == True and scrape_pulls_success == True:
    # append diff info dataset to DB
    dbg.log(
      "", "start diff_writer: " + repo_owner_name + "/" + repo_name)
    diff_writer_success = scraping.diff_writer(mongo_client, repo)
    dbg.log("", "finished diff_writer (success->" + str(
      diff_writer_success) + "): " + repo_owner_name + "/" + repo_name)
    if diff_writer_success == True:
      db_repos.update_one(
        {
          'ID': repo["ID"]
        }, {'$set': {
          "scraped_flag": True
        }},
        upsert=False)

  mongo_client.close()

  return True



########
# Main #
########

if __name__ == '__main__':
  global token_q

  argvs = sys.argv
  argc = len(argvs)

  dbg.log("", "start main script")

  if(argc != 2):
    dbg.log("", "Usage: ./run.sh {# of processes}")
    N_processes = multi.cpu_count()
    dbg.log("", "set processes to " + str(N_processes))
  else:
    N_processes = int(argvs[1])
  
  with Pool(processes=N_processes) as pool:

    while True:

      mongo_client = MongoClient(env.mongo_uri)
      db = mongo_client[env.db_name]

      repos = list(db[env.col_repos].find({"scraped_flag":False}))

      mongo_client.close()

      if len(repos) == 0:
        break

      try:
        send_slack_notification("Top of Data Collector Loop")
        results = [pool.apply_async(process, (repo,)) for repo in repos]
        output = [r.get() for r in results]
        print(output)
      except KeyboardInterrupt as e:
        dbg.log("SIGINT")
        break
      except:
        if sys.exc_info()[0].__name__ == "AutoReconnect":
          dbg.log("ERR", sys.exc_info()[0].__name__)
          send_slack_notification(sys.exc_info()[0].__name__ + " CONTINUE")
          continue
        elif sys.exc_info()[0].__name__ == "ConnectionResetError":
          dbg.log("ERR", sys.exc_info()[0].__name__)
          send_slack_notification(sys.exc_info()[0].__name__ + " CONTINUE")
          continue
        dbg.log("ERR", sys.exc_info()[0].__name__)
        send_slack_notification(sys.exc_info()[0].__name__)
        raise

  dbg.log("", "finished main script")