

import requests
import configparser
import click
import os
import sys
import json


TOKEN = ''
LABELS = []
REPOS = []


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def token_auth(req):
    req.headers['Authorization'] = 'token ' + TOKEN
    req.headers['Content-Type'] = 'application/json'
    return req


def process_config_file(config_file):
    labels = {}

    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(config_file.name)
    rep = []
    for key in config['repos']:
        if config['repos'].getboolean(key):
            rep.append(key)

    curent_token = config['github']['token']

    if "others" in config:
        print("repo")
        labels = get_labels(config['others']['template-repo'])
    elif "labels" in config:
        for key in config['labels']:
            labels[key] = config['labels'][key]

    return curent_token, rep, labels


@click.option('-t', '--token', default=lambda: os.environ.get('GITHUB_TOKEN', ''),
              help="Your token for comunication with github API")
@click.option('-c', '--config', type=click.File('r'), help="Path to load config file use INI format")
@click.option('-r', '--template-repo', default='', help="Define template repository name")
@click.option('-a', '--all-repos', is_flag=True)
@click.group()
def cli(token, config, template_repo, all_repos):

    curent_token = ''
    repos = []
    labels = {}

    if config:
        curent_token, repos, labels = process_config_file(config)

    if len(token) > 0:
        curent_token = token

    if all_repos:
        repos = get_all_repos()

    if len(curent_token) == 0:
        eprint('No GitHub token has been provided')
        exit(3)

    if len(repos) == 0:
        eprint('No repositories specification has been found')
        exit(7)

    global TOKEN, REPOS, LABELS
    TOKEN = curent_token
    REPOS = repos

    if len(template_repo) > 0:
        labels = get_labels(str(template_repo))

    LABELS = labels

    pass


@click.command()
def list_repos():
    repos = get_all_repos()
    for repo in repos:
        print(repo)


@click.command()
@click.argument('repository_name')
def list_labels(repository_name):
    labels = get_labels(repository_name)
    for key in labels:
        print('#'+labels[key]+' '+key)


@click.command()
@click.argument('mode', type=click.Choice(['update', 'replace']))
def run(mode):
    if mode == "update":
        for repo in REPOS:
            update_labels(LABELS, repo)

    elif mode == "replace":
        for repo in REPOS:
            replace_labels(LABELS, repo)



cli.add_command(list_repos)
cli.add_command(list_labels)
cli.add_command(run)


def update_label(repository_name, label_name, color):
    session = requests.Session()
    session.headers = {'User-Agent': 'Python'}
    session.auth = token_auth
    data = json.dumps({
        'color': color
    })
    r = session.patch('https://api.github.com/repos/'+repository_name+'/labels/'+label_name, data=data)

    if 200 <= r.status_code <= 299:
        print("[UPD][SUC] "+repository_name+"; "+label_name+"; "+color)
    else:
        print(r.status_code)
        print("[UPD][ERR] " + repository_name + "; " + str(r.status_code) + " - Not Found")


def create_label(repository_name, label_name, color):
    session = requests.Session()
    session.headers = {'User-Agent': 'Python'}
    session.auth = token_auth
    data = json.dumps({
        "name": label_name,
        "color": color
    })
    r = session.post('https://api.github.com/repos/' + repository_name + '/labels', data=data)
    if r.status_code >= 200 and r.status_code <= 299:
        print("[ADD][SUC] " + repository_name + "; " + label_name + "; " + color)
    else:
        print("[ADD][ERR] " + repository_name + "; " + str(r.status_code) + "-" + r.json()['message'])


def remove_labels(repository_name, label_name):
    session = requests.Session()
    session.headers = {'User-Agent': 'Python'}
    session.auth = token_auth
    r = session.delete('https://api.github.com/repos/' + repository_name + '/labels/'+label_name)
    if 200 <= r.status_code <= 299:
        print("[DEL][SUC] " + repository_name + "; " + label_name)
    else:
        print("[DEL][ERR] " + repository_name + "; " + str(r.status_code) + " -" + r.json()['message'])


def get_labels(repository_name):
    labels = {}
    session = requests.Session()
    session.headers = {'User-Agent': 'Python'}
    session.auth = token_auth
    r = session.get('https://api.github.com/repos/' + repository_name + '/labels')
    if 200 <= r.status_code <= 299:
        data = json.loads(r.text)
        for label in data:
            labels[str(label['name'])] = str(label['color'])
    else:
        print("[LBL][ERR] " + repository_name + "; " + str(r.status_code) + " -" + r.json()['message'])

    return labels


def get_all_repos():
    repos = []

    session = requests.Session()
    session.headers = {'User-Agent': 'Python'}
    session.auth = token_auth
    r = session.get('https://api.github.com/user/repos')
    for repo in r.json():
        repos.append(repo['full_name'])

    return repos


def update_labels(pattern_label, repository_name):
    labels = get_labels(repository_name)
    for key in pattern_label:

        if key in labels.keys():
            if labels[key] == pattern_label[key]:
                continue
            else:
                update_label(repository_name, key, pattern_label[key])
        else:
            create_label(repository_name, key, pattern_label[key])


def replace_labels(pattern_label, repository_name):
    labels = get_labels(repository_name)

    for key in pattern_label:
        if key in labels.keys():
            if labels[key] == pattern_label[key]:
                del labels[key]
                continue
            else:
                update_label(repository_name, key, pattern_label[key])
                del labels[key]
        else:
            create_label(repository_name, key, pattern_label[key])

    for key in labels:
        remove_labels(repository_name, key)


if __name__ == '__main__':
    cli()
