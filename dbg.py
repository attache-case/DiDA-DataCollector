# coding:utf-8

from datetime import datetime
import logging

## debug outputs

# basicConfigのformat引数でログのフォーマットを指定する
log_fmt = '%(asctime)s- %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(filename='debug.log', format=log_fmt, level=logging.DEBUG)


def time_now():

    logging.info(datetime.now().strftime('%Y/%m/%d %H:%M:%S'))


def log(TYPE="", s="", t=""):

    if TYPE == "":
        logging.info(s)
    elif TYPE == "API/ERR":
        logging.info("API ERROR: %s", s)
    elif TYPE == "API/RETRY":
        logging.info("RETRY API CALL(%s)", s)
    elif TYPE == "API/GIVEUP":
        logging.error("REACHED LIMIT OF API RETRY. GIVEUP.")
    elif TYPE == "ILLDATA":
        logging.error("INCORRECT DATA")
    elif TYPE == "TARGET/ERR":
        logging.error("INVALID TARGET STRING: %s", s)
    elif TYPE == "TOK/REST":
        logging.info("REST TOKEN %s", s)
    elif TYPE == "MORE":
        logging.info("More than 100 %s to scrape for %s ID(s)", s, t)
    elif TYPE == "UPDATE/BATCH/OFERR":
        logging.info("OperationFailure (nextCursor:%s repo:%s)", s, t)
    elif TYPE == "UPDATE/BATCH/RQERR":
        logging.info("TooManyRequests -> sleep5 -> retry (nextCursor:%s repo:%s)", s, t)
    elif TYPE == "UPDATE/BATCH/TOERR":
        logging.info("ExecutionTimeout (nextCursor:%s repo:%s)", s, t)
    elif TYPE == "UPDATE/OFERR":
        logging.info("OperationFailure (ID:%s repo:%s)", s, t)
    elif TYPE == "UPDATE/WERR":
        logging.info("WriteError (ID:%s repo:%s)", s, t)
    elif TYPE == "UPDATE/LERR":
        logging.info("DocumentTooLarge (ID:%s repo:%s)", s, t)
    elif TYPE == "UPDATE/SKIP":
        logging.info("Exception while writing node %s", s)
    elif TYPE == "DIFF-COMMIT/ERR":
        logging.info("CalledProcessError(no commit?)(index:%d, oid:%s)", s, t)
    elif TYPE == "DIFF-COMMIT/OFERR":
        logging.info("OperationFailure (index:%d, oid:%s)", s, t)
    elif TYPE == "DIFF-COMMIT/WERR":
        logging.info("WriteError (index:%d, oid:%s)", s, t)
    elif TYPE == "DIFF-COMMIT/LERR":
        logging.info("DocumentTooLarge (index:%d, oid:%s)", s, t)
    elif TYPE == "DIFF-COMMIT/UCERR":
        logging.info("UnicodeDecodeError (index:%d, oid:%s)", s, t)
    elif TYPE == "SIGINT":
        logging.info("==KeyboardInterrupt==")
