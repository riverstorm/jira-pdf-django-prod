from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from main.models import *
import json, jwt
from django.conf import settings


def extract_data(data):
    body = json.loads(data.body.decode('utf-8'))
    content = jwt.decode(body.get('jwt'), verify=False)
    return body, content

def get_account(data):
    try:
        debug = data.GET.get('debug')
        if debug and settings.DEBUG:
            return Account.objects.get(id=2, client_key='debug')
        body = json.loads(data.body.decode('utf-8'))
        content = jwt.decode(body.get('jwt'), verify=False)
        account = Account.objects.get(
            client_key=content.get('iss')
        )
        if account:
            verified = jwt.decode(body.get('jwt'), account.shared_secret, algorithms=['HS256'])    
            if verified:
                return account
    except:
        return False

def get_project_issue(debug, data):
    if debug and settings.DEBUG:
        return 1, 1
    body, content = extract_data(data)
    project_id = content.get('context').get('jira').get('project').get('id')
    ticket_id = content.get('context').get('jira').get('issue').get('id')
    return project_id, ticket_id

def get_project_issue_obj(project_id, ticket_id):
    project = Project.objects.filter(
        account=account,
        project_id=project_id
    ).first()
    if not project:
        return False, False
    ticket = Ticket.objects.filter(
        project=project,
        ticket_id=ticket_id
    ).first()
    if not ticket:
        return False, False
    return project, ticket