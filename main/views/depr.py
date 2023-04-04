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
            print('no debug')
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


def list_todos(ticket):
    full_list = []
    todo_lists = TodoList.objects.filter(
        ticket=ticket
    ).order_by('index').all()
    if todo_lists:
        for todo_list in todo_lists:
            single_list = {
                'id': todo_list.id,
                'title': todo_list.title,
                'index': float(todo_list.index),
                'todos': []
            }
            todos = Todo.objects.all().filter(
                todo_list=todo_list
            ).order_by('index').all()
            if todos:
                for todo in todos:
                    single_list['todos'].append({
                        'id': todo.id,
                        'value': todo.value,
                        'completed': todo.completed,
                        'index': float(todo.index)
                    })
            full_list.append(single_list)
    return full_list


def new_todo_order(todo_list):
    # Get latest index
    last_todo = Todo.objects.filter(
        todo_list=todo_list
    ).order_by('-index').all()
    # Set id for new index
    if last_todo:
        return last_todo[0].index + 65536
    # else	
    return 65536

def new_list_order(ticket):
    # Get latest index
    last_todo_list = TodoList.objects.filter(
        ticket=ticket
    ).order_by('-index').all()
    # Set id for new index
    if last_todo_list:
        return last_todo_list[0].index + 65536
    # else	
    return 65536


@csrf_exempt
def todo_list(request):
    try:
        debug = request.GET.get('debug')
        account = get_account(request)
        if account:
            project_id, ticket_id = get_project_issue(debug, request)
            project = Project.objects.filter(
                account=account,
                project_id=project_id
            ).first()
            if not project:
                return JsonResponse([], safe=False)
            ticket = Ticket.objects.filter(
                project=project,
                ticket_id=ticket_id
            ).first()
            if not ticket:
                return JsonResponse([], safe=False)
            if ticket:
                full_list = list_todos(ticket)
                return JsonResponse(full_list, safe=False)
    except Exception as e:
        print(e)
    return JsonResponse(False, safe=False, status=500)


@csrf_exempt
def todo_create(request):
    try:
        debug = request.GET.get('debug')
        account = get_account(request)
        if account:
            project_id, ticket_id = get_project_issue(debug, request)
            todo_value = json.loads(request.body).get('value')
            todo_list = json.loads(request.body).get('todo_list')
            print(todo_list)
            if project_id and ticket_id and todo_value:
                project, _ = Project.objects.get_or_create(
                    account=account,
                    project_id=project_id,
                    defaults={'account': account, 'project_id': project_id}
                )
                ticket, _ = Ticket.objects.get_or_create(
                    project=project,
                    ticket_id=ticket_id,
                    defaults={'project': project, 'ticket_id': ticket_id}
                )
                if todo_list == 0:
                    todo_list_obj = TodoList.objects.create(
                        ticket=ticket,
                        title='Todo list',
                        index=new_list_order(ticket)
                    )
                else:
                    todo_list_obj = TodoList.objects.get(
                        ticket=ticket,
                        id=todo_list
                    )
                if todo_list_obj:
                    todo = Todo.objects.create(
                        todo_list=todo_list_obj,
                        value=todo_value,
                        index=new_todo_order(todo_list_obj)
                    )
                    if todo and ticket:
                        full_list = list_todos(ticket)
                        return JsonResponse(full_list, safe=False)
    except Exception as e:
        print(e)
    return JsonResponse(False, safe=False, status=500)


@csrf_exempt
def todo_edit(request):
    try:
        debug = request.GET.get('debug')
        account = get_account(request)
        if account:
            project_id, ticket_id = get_project_issue(debug, request)
            todo_id = json.loads(request.body).get('id')
            todo_list_id = json.loads(request.body).get('todo_list')
            todo_value = json.loads(request.body).get('value')
            todo_checked = json.loads(request.body).get('checked')
            if project_id and ticket_id and todo_id and todo_list_id:
                project = Project.objects.get(
                    account=account,
                    project_id=project_id
                )
                ticket = Ticket.objects.get(
                    project=project,
                    ticket_id=ticket_id
                )
                todo_list = TodoList.objects.get(
                    ticket=ticket,
                    id=todo_list_id
                )
                todo = Todo.objects.get(
                    todo_list=todo_list,
                    id=todo_id
                )
                todo.value = todo_value
                todo.completed = todo_checked
                todo.save()
                if ticket:
                    full_list = list_todos(ticket)
                    return JsonResponse(full_list, safe=False)
    except Exception as e:
        print(e)
    return JsonResponse(False, safe=False, status=500)


@csrf_exempt
def todo_delete(request):
    try:
        debug = request.GET.get('debug')
        account = get_account(request)
        if account:
            project_id, ticket_id = get_project_issue(debug, request)
            todo_id = json.loads(request.body).get('id')
            todo_list_id = json.loads(request.body).get('todo_list')

            if project_id and ticket_id and todo_id and todo_list_id:
                project = Project.objects.get(
                    account=account,
                    project_id=project_id
                )
                ticket = Ticket.objects.get(
                    project=project,
                    ticket_id=ticket_id
                )
                todo_list = TodoList.objects.get(
                    ticket=ticket,
                    id=todo_list_id
                )
                todo = Todo.objects.get(
                    todo_list=todo_list,
                    id=todo_id
                )
                result = todo.delete()
                if result and ticket:
                    full_list = list_todos(ticket)
                    return JsonResponse(full_list, safe=False)

    except Exception as e:
        print(e)
    return JsonResponse(False, safe=False, status=500)


@csrf_exempt
def todo_order(request):
    try:
        debug = request.GET.get('debug')
        account = get_account(request)
        if account:
            project_id, ticket_id = get_project_issue(debug, request)
            todo_id = json.loads(request.body).get('id')

            # Get moving details
            new_todo_list = json.loads(request.body).get('new_todo_list')
            previous_todo_list = json.loads(request.body).get('old_todo_list')
            new_todo_index = json.loads(request.body).get('new_todo_index') + 1
            #old_todo_index = json.loads(request.body).get('old_todo_index')

            project = Project.objects.get(
                account=account,
                project_id=project_id
            )
            ticket = Ticket.objects.get(
                project=project,
                ticket_id=ticket_id
            )

            # Get old and new list
            if new_todo_list != previous_todo_list:
                new_todo_list = TodoList.objects.get(
                    ticket=ticket,
                    id=new_todo_list
                )
                previous_todo_list = TodoList.objects.get(
                    ticket=ticket,
                    id=previous_todo_list
                )
            else:
                new_todo_list = TodoList.objects.get(
                    ticket=ticket,
                    id=new_todo_list
                )
                previous_todo_list = new_todo_list

            # Get todo item
            todo = Todo.objects.get(todo_list=previous_todo_list, id=todo_id)
        
        # If new index is 1
        if new_todo_index is 1:
            # Get all todos of new list
            last_index = Todo.objects.filter(
                todo_list=new_todo_list
            ).order_by('index').all()
            if last_index:
                # Get index of previous leading todo
                last_index = last_index[0].index
                if last_index >= 2:
                    new_index = last_index / 2
                else:
                    # Recalculate indexes
                    todos = Todo.objects.filter(
                        todo_list=new_todo_list
                    ).order_by('index').all()
                    for i, item in enumerate(todos, start=1):
                        item.index = i * 65536
                        item.save()
                    last_index = Todo.objects.filter(
                        todo_list=new_todo_list
                    ).order_by('index').all()
                    if last_index:
                        last_index = last_index[0].index
                    if last_index >= 2:
                        new_index = last_index / 2
            else:
                new_index = 65536

        # Else if new index greater 1
        if new_todo_index >= 2:
            todos = Todo.objects.filter(
                todo_list=new_todo_list
            ).order_by('index').all()
            previous_index = 0
            for item in todos:
                previous_index = previous_index + 1
                if item.id == todo.id:
                    break
            if previous_index > new_todo_index:
                previous_todo = todos[(new_todo_index - 2)].index
            elif new_todo_list != previous_todo_list:
                previous_todo = todos[(new_todo_index - 2)].index
            else:
                previous_todo = todos[(new_todo_index - 1)].index
            if len(todos) > new_todo_index:
                if previous_index > new_todo_index:
                    following_todo = todos[(new_todo_index - 1)].index
                else:
                    following_todo = todos[(new_todo_index)].index
                if (following_todo - previous_todo) >= 2:
                    new_index = previous_todo + (following_todo - previous_todo) / 2
                else:
                    todos = Todo.objects.filter(
                        todo_list=new_todo_list
                    ).order_by('index').all()
                    for i, item in enumerate(todos, start=1):
                        item.index = i * 65536
                        item.save()
                    previous_todo = todos[(new_todo_index - 2)]
                    if len(todos) >= new_todo_index:
                        following_todo = todos[(new_todo_index)]
                        if (following_todo - previous_todo) >= 2:
                            new_index = previous_todo + ((following_todo - previous_todo) / 2)
            else:
                new_index = previous_todo + 65536
        todo.todo_list = new_todo_list
        todo.index = new_index
        todo.save()

        # Return full todo lists
        full_list = list_todos(ticket)
        return JsonResponse(full_list, safe=False)

    except Exception as e:
        print(e)
    return JsonResponse(False, safe=False, status=500)


@csrf_exempt
def list_create(request):
    try:
        debug = request.GET.get('debug')
        print(debug)
        account = get_account(request)
        if account:
            project_id, ticket_id = get_project_issue(debug, request)
            list_title = json.loads(request.body).get('title')

            if project_id and ticket_id and list_title:
                project, _ = Project.objects.get_or_create(
                    account=account,
                    project_id=project_id,
                    defaults={'account': account, 'project_id': project_id}
                )
                ticket, _ = Ticket.objects.get_or_create(
                    project=project,
                    ticket_id=ticket_id,
                    defaults={'project': project, 'ticket_id': ticket_id}
                )
                todo_list_obj = TodoList.objects.create(
                    ticket=ticket,
                    title=list_title,
                    index=new_list_order(ticket)
                )
                if todo_list_obj:
                    full_list = list_todos(ticket)
                    return JsonResponse(full_list, safe=False)
    except Exception as e:
        print(e)
    return JsonResponse(False, safe=False, status=500)


@csrf_exempt
def list_edit(request):
    try:
        debug = request.GET.get('debug')
        account = get_account(request)
        if account:
            project_id, ticket_id = get_project_issue(debug, request)
            todo_list_id = json.loads(request.body).get('todo_list')
            list_title = json.loads(request.body).get('title')
            if project_id and ticket_id and todo_list_id and list_title:
                project = Project.objects.get(
                    account=account,
                    project_id=project_id
                )
                ticket = Ticket.objects.get(
                    project=project,
                    ticket_id=ticket_id
                )
                todo_list = TodoList.objects.get(
                    ticket=ticket,
                    id=todo_list_id
                )
                todo_list.title = list_title
                todo_list.save()
                if ticket:
                    full_list = list_todos(ticket)
                    return JsonResponse(full_list, safe=False)
    except Exception as e:
        print(e)
    return JsonResponse(False, safe=False, status=500)


@csrf_exempt
def list_delete(request):
    try:
        debug = request.GET.get('debug')
        account = get_account(request)
        if account:
            project_id, ticket_id = get_project_issue(debug, request)
            todo_list_id = json.loads(request.body).get('todo_list')

            if project_id and ticket_id and todo_list_id:
                project = Project.objects.get(
                    account=account,
                    project_id=project_id
                )
                ticket = Ticket.objects.get(
                    project=project,
                    ticket_id=ticket_id
                )
                todo_list = TodoList.objects.get(
                    ticket=ticket,
                    id=todo_list_id
                )
                todo_list.delete()
                if ticket:
                    full_list = list_todos(ticket)
                    return JsonResponse(full_list, safe=False)
    except Exception as e:
        print(e)
    return JsonResponse(False, safe=False, status=500)