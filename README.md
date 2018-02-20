# DiDA-DataCollector

## Usage
### preparation
```bash
git clone https:/github.com/attache-case/DiDA-DataCollector.git
cd DiDA-DataCollector
screen -S scraping # use screen
chmod 755 ./run.sh
```
- modify `env.py`
  - Please request @attache-case for MongoDB Connection String
    - replace "PLEASE_ASK_ADMIN_FOR_CONNECTION_STRING" with the string
  - Please fill your GitHub Personal Access Token
    - add your token info to `personal_access_token_list`
- modify `main.py`
  1. Create your Slack webhook to get error info
  1. replace "WRITE_YOUR_SLACK_WEBHOOK_URL" under `def send_slack_notification(s):`

### run script
```bash
git clone https:/github.com/attache-case/DiDA-DataCollector.git
cd DiDA-DataCollector
screen -S scraping # use screen
chmod 755 ./run.sh
./run.sh N_PROCESSORS # start script
(keyboard) ^A-d # detach
screen -r scraping # re-attach
```
N_PROCESSORS: # of processors to use for multi-thread data collecting (default -> # of cpu)

## Requirements
- Machine
  - Linux
- Environment
  - Python3.5
    - numpy
    - pandas
    - ipywidgets
    - pymongo
