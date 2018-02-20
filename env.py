# coding: utf-8

## mongoDB connection string

# ASK physical.chemistry.12@gmail.com for our mongoDB connection string

mongo_uri = "PLEASE_ASK_ADMIN_FOR_CONNECTION_STRING"



## Database Relational Strings

db_name = "githubCodeDB"
col_repos = "Repositories"
col_issues = "Issues"
col_pulls = "PullRequests"
col_commits = "Commits"
col_users = "Users"



## Scraping Target Strings

str_target_issue = "issues"
str_target_pull = "pullRequests"



## Personal tokens to use GitHub API

# add your token info as dictionary object to the list below
# copy this template and fill your token information
#
# {
# 	"name":
# 	"ANY_NAME_TO_IDENTIFY_YOUR_TOKEN",
# 	"token":
# 	"YOUR_ACCESS_TOKEN"
# }

personal_access_token_list = [

]



## base query string

def readQueryString(_filename):

	s = ""
	try:
		with open(_filename) as query_json_file:
			s = query_json_file.read()
	except:
		pass
	s = s.replace("\t", " ")
	s = s.replace(" ","")
	s = s.replace("%", " %")
	s = s.replace("\" ", "\"")
	s = s.replace("...on", "... on ")
	s = s.replace("\n", " ")
	return s

# initialize query_issue_master
query_issue_master = readQueryString('GraphQL_query_issue_master.txt')

# initialize query_pull_master
query_pull_master = readQueryString('GraphQL_query_pull_master.txt')

# initialize subquery_master
subquery_issue_master = readQueryString('GraphQL_subquery_issue_master.txt')
subquery_pull_master = readQueryString('GraphQL_subquery_pull_master.txt')

# initialize sub queries
subquery = dict(
	labels = readQueryString('GraphQL_subquery_labels.txt'),
	comments = readQueryString('GraphQL_subquery_comments.txt'),
	timeline_issue = readQueryString('GraphQL_subquery_timeline_issue.txt'),
	timeline_pull = readQueryString('GraphQL_subquery_timeline_pull.txt'),
	reactions = readQueryString('GraphQL_subquery_reactions.txt'),
	commits = readQueryString('GraphQL_subquery_commits.txt'),
	reviews = readQueryString('GraphQL_subquery_reviews.txt'),
	pageInfo = readQueryString('GraphQL_subquery_pageInfo.txt')
)
subquery_keys = dict(
	issue = ["labels", "comments", "timeline_issue", "reactions"],
	pull = ["labels", "comments", "commits", "timeline_pull", "reactions", "reviews"]
)
subquery_target = dict(
	labels = "labels",
	comments = "comments",
	timeline_issue = "timeline",
	timeline_pull = "timeline",
	reactions = "reactions",
	commits = "commits",
	reviews = "reviews"
)

# initialize query_limit
query_limit = readQueryString('GraphQL_query_limit.txt')

# params to be embedded
number_of_scraping_issues = 50
number_of_scraping_pulls  = 50

# API call config
MAX_RETRY = 5
LIMIT_CUTOFF = 100