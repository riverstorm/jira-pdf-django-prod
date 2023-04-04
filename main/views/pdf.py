from django.http import JsonResponse, FileResponse, HttpResponse
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from main.models import *
import json, jwt, time, requests, base64, datetime, io, math, sys, secrets
from main.views.helper import *
from main.jwt_auth import auth_required
from jinja2 import Template
from dateutil import parser
from bs4 import BeautifulSoup
from PIL import Image
from sentry_sdk import capture_exception
from multiprocessing.dummy import Pool as ThreadPool
from itertools import repeat
import logging


def get_jira_access_token(client, claims):
    now = int(time.time())
    token = jwt.encode(key=client.shared_secret, algorithm='HS256', payload={
        'iss': 'urn:atlassian:connect:clientid:' + client.oauth_client_id,
        'sub': 'urn:atlassian:connect:useraccountid:' + claims['sub'],
        'tnt': client.base_url,
        'aud': 'https://oauth-2-authorization-server.services.atlassian.com',
        'exp': now + 60,
        'iat': now
    })
    auth_url = 'https://oauth-2-authorization-server.services.atlassian.com/oauth2/token'
    data = {
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        'assertion': token,
        'scope': 'READ'
    }
    r = requests.post(auth_url, data=data)
    if not r.ok:
        raise Exception('oauth2 failed', r.content)
    r_json = r.json()
    if not r_json.get('access_token'):
        raise Exception('oauth2 failed', 'no access token available', r.content)
    return r_json.get('access_token')


def get_jira_issue(client, claims):
    access_token = get_jira_access_token(client, claims)
    issue_url = client.base_url + '/rest/api/2/issue/' + claims['context']['jira']['issue']['id'] + '?expand=renderedFields'
    headers = {
        'Authorization': 'Bearer ' + access_token,
        'Accept': 'application/json'
    }
    r = requests.get(issue_url, headers=headers)
    if not r.ok:
        print(r.status_code, r.content)
        raise Exception('issue retrieval failed', r.content)
    r_json = r.json()
    return r_json, access_token


def get_pdf(client, claims, html):
    access_token = get_jira_access_token(client, claims)
    data = {
        'html': html,
        'token': access_token
    }
    url = 'http://23.88.110.197:6000/generate/pdf'
    r = requests.post(url, json=data)
    if not r.ok:
        print(r.status_code, r.content)
        raise Exception('pdf generation failed', r.content)
    r_json = r.content
    return r_json


def build_html(issue, settings, custom_template, attachments, images, project_name):
    approval_date = ''
    if custom_template:
        try:
            fields = issue.get('fields')
            if fields:
                items = fields.get('customfield_10027')
                if items:
                    for item in items:
                        if item['name'] == 'Review':
                            approval_date = item['completedDate']['iso8601']
        except:
            pass

        with open('files/c_incident_form_1.html', 'r') as f:
            created_dt = datetime.datetime.strptime(issue['fields']['created'], '%Y-%m-%dT%H:%M:%S.%f%z')
            updated_dt = datetime.datetime.strptime(issue['fields']['updated'], '%Y-%m-%dT%H:%M:%S.%f%z')
            template = Template(f.read())
    else:
        with open('files/email_template.html', 'r') as f:
            created_dt = datetime.datetime.strptime(issue['fields']['created'], '%Y-%m-%dT%H:%M:%S.%f%z')
            updated_dt = datetime.datetime.strptime(issue['fields']['updated'], '%Y-%m-%dT%H:%M:%S.%f%z')
            template = Template(f.read())

    if issue['fields'].get('customfield_10197'):
        customfield_10197_value = issue['fields'].get('customfield_10197').get('value')
    else:
        customfield_10197_value = ''

    if issue['fields'].get('customfield_10266'):
        assessed_by = issue['fields'].get('customfield_10266').get('displayName', '')
    else:
        assessed_by = ''

    if issue['fields'].get('customfield_10267'):
        escalation_req = issue['fields'].get('customfield_10267').get('value', '')
    else:
        escalation_req = ''

    if issue['fields'].get('customfield_10268'):
        implemented_by = issue['fields'].get('customfield_10268').get('displayName', '')
    else:
        implemented_by = ''

    if issue['fields'].get('customfield_10270'):
        cause_assessed_by = issue['fields'].get('customfield_10270').get('displayName', '')
    else:
        cause_assessed_by = ''

    if issue['fields'].get('customfield_10273'):
        customfield_10273 = issue['fields'].get('customfield_10273').get('displayName', '')
    else:
        customfield_10273 = ''

    if issue['fields'].get('customfield_10275'):
        customfield_10275 = issue['fields'].get('customfield_10275').get('displayName', '')
    else:
        customfield_10275 = ''

    if issue['fields'].get('customfield_10309'):
        if len(issue['fields'].get('customfield_10309')) > 0:
            customfield_10309 = issue['fields'].get('customfield_10309')[0].get('value', '')
        else:
            customfield_10309 = ''
    else:
        customfield_10309 = ''
    if customfield_10309 == '':
        customfield_10309 = issue['fields'].get('customfield_10295', '')

    return template.render(
        issue,
        created_dt=created_dt,
        updated_dt=updated_dt,
        attachments=attachments,
        images=images,
        project_name=project_name,
        settings=settings,
        approval_date=approval_date,
        values={
            'customfield_10047': issue['fields'].get('customfield_10047', ''),
            'customfield_10295': issue['fields'].get('customfield_10295', ''),
            'customfield_10265': issue['fields'].get('customfield_10265', ''),
            'customfield_10197_value': customfield_10197_value,
            'customfield_10266': assessed_by,
            'customfield_10267': escalation_req,
            'customfield_10278': issue['fields'].get('customfield_10278', ''),
            'customfield_10268': implemented_by,
            'customfield_10285': issue['fields'].get('customfield_10285', ''),
            'customfield_10212': issue['fields'].get('customfield_10212', ''),
            'customfield_10270': cause_assessed_by,
            'customfield_10283': issue['fields'].get('customfield_10283', ''),
            'customfield_10047': issue['fields'].get('customfield_10047', ''),
            'customfield_10273': customfield_10273,
            'customfield_10282': issue['fields'].get('customfield_10282', ''),
            'customfield_10275': customfield_10275,
            'customfield_10272': issue['fields'].get('customfield_10272', ''),
            'customfield_10309': customfield_10309
        }
    )


def replace_links_get_images(data, access_token):
    r = requests.get(data['content'], headers={'Authorization': 'Bearer ' + access_token})
    img = None
    if r.ok:
        img = base64.b64encode(r.content).decode('utf-8')
        img = 'data:image/png;base64,' + img
    return {
        'src': data['src'],
        'image': img
    }


def replace_links(issue, base_url, access_token, settings):
    soup = BeautifulSoup(issue['renderedFields']['description'], 'html.parser')
    if settings['attachmentsLinks']:
        html_markup = '''
            <div class="img-flow"><a href="">
                <div class="img-link">
                    <svg width="15px" height="15px" xmlns="http://www.w3.org/2000/svg" class="ionicon" viewBox="0 0 512 512"><title>Open</title><path d="M384 224v184a40 40 0 01-40 40H104a40 40 0 01-40-40V168a40 40 0 0140-40h167.48M336 64h112v112M224 288L440 72" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="32"/></svg>
                </div>
                <img src="" style="border-radius:3px;">
            </a></div>
        '''
    else:
        html_markup = '''
            <div class="img-flow">
                <img src="" style="border-radius:3px;">
            </div>
        '''
    images = soup.find_all('span', class_='image-wrap')
    image_list = []
    request_list = []
    for i in images:
        src = i.find('img')['src']
        if base_url in src:
            full_url = src
        else:
            full_url = base_url + src
        request_list.append({
            'src': src,
            'content': full_url,
            'image': None
        })
        
    pool = ThreadPool(10)
    result_images = pool.starmap(replace_links_get_images, zip(request_list, repeat(access_token)))
    pool.close() 
    pool.join()

    for i in images:
        src = i.find('img')['src']
        for r in result_images:
            if src == r['src']:
                if base_url in src:
                    full_url = src
                else:
                    full_url = base_url + src
                image_list.append({
                    'src': src,
                    'image': r['image']
                })
                markup = BeautifulSoup(html_markup, 'html.parser')
                markup.find('img')['src'] = r['image']
                if settings['attachmentsLinks']:
                    markup.find('a')['href'] = full_url
                i.replace_with(markup)

    issue['renderedFields']['description'] = soup
    return issue, image_list


def replace_comments_links(issue, base_url, access_token, settings):
    image_list = []
    for idx, comment in enumerate(issue['renderedFields']['comment']['comments']):
        soup = BeautifulSoup(comment['body'], 'html.parser')
        if settings['commentImages']:
            img_style = 'max-width:100%;'
        else:
            img_style = 'max-width:300px;max-height:300px;'
        if settings['attachmentsLinks']:
            html_markup = '''
                <div class="img-flow"><a href="">
                    <div class="img-link">
                        <svg width="15px" height="15px" xmlns="http://www.w3.org/2000/svg" class="ionicon" viewBox="0 0 512 512"><title>Open</title><path d="M384 224v184a40 40 0 01-40 40H104a40 40 0 01-40-40V168a40 40 0 0140-40h167.48M336 64h112v112M224 288L440 72" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="32"/></svg>
                    </div>
                    <img src="" style="border-radius:3px;{style}">
                </a></div>
            '''.format(style=img_style)
        else:
            html_markup = '''
                <div class="img-flow">
                    <img src="" style="border-radius:3px;{style}">
                </div>
            '''.format(style=img_style)
        images = soup.find_all('span', class_='image-wrap')


        image_list = []
        request_list = []
        for i in images:
            if base_url in i.find('img')['src']:
                full_url = i.find('img')['src']
            else:
                full_url = base_url + i.find('img')['src']
            request_list.append({
                'src': i.find('img')['src'],
                'content': full_url,
                'image': None
            })
            
        pool = ThreadPool(10)
        result_images = pool.starmap(replace_links_get_images, zip(request_list, repeat(access_token)))
        pool.close() 
        pool.join()

        for i in images:
            src = i.find('img')['src']
            for r in result_images:
                if src == r['src']:
                    if base_url in src:
                        full_url = src
                    else:
                        full_url = base_url + src
                    image_list.append({
                        'src': src,
                        'image': r['image']
                    })
                    markup = BeautifulSoup(html_markup, 'html.parser')
                    markup.find('img')['src'] = r['image']
                    if settings['attachmentsLinks']:
                        markup.find('a')['href'] = full_url
                    i.replace_with(markup)

        issue['renderedFields']['comment']['comments'][idx]['body'] = soup
    return issue, image_list


def optimize_images(img_data, img_type, width):
    img_data = io.BytesIO(img_data)
    img_opt = io.BytesIO()
    img_data = Image.open(img_data)
    w, h = img_data.size
    ratio = w / h
    if w > width:
        img_data = img_data.resize((width, math.ceil(width / ratio)), Image.ANTIALIAS)
    img_data.save(img_opt, img_type, optimize=True, quality=80)
    return img_opt.getvalue()


def load_image(data, access_token, optimize):
    r = requests.get(data['content'], headers={'Authorization': 'Bearer ' + access_token})
    img = None
    if r.ok:
        if optimize == 'True':
            img_opt = optimize_images(r.content, data['mimeType'].split('/')[1], 1200)
            img = base64.b64encode(img_opt).decode('utf-8')
        else:
            img = base64.b64encode(r.content).decode('utf-8')
        img = 'data:' + data['mimeType'] + ';base64,' + img
    return {
        'content': data['content'],
        'image': img
    }


def build_attachments(issue, access_token):
    attachments = issue['renderedFields']['attachment']
    attachments_list = []
    request_list = []
    for a in attachments:
        img = None
        if a['mimeType'].split('/')[1] in ['jpg', 'jpeg', 'png']:
            if a.get('thumbnail'):
                request_list.append(a)

    pool = ThreadPool(10)
    result_images = pool.starmap(load_image, zip(request_list, repeat(access_token), repeat('False')))
    pool.close() 
    pool.join()

    for a in attachments:
        img = None
        if a['mimeType'].split('/')[1] in ['jpg', 'jpeg', 'png']:
            if a.get('thumbnail'):
                for r in result_images:
                    if a['content'] == r['content']:
                        img = r['image']
                        break
        attachments_list.append({
            'name': a['filename'].split('.')[0][:10] + '... .' + a['mimeType'].split('/')[1],
            'image': img,
            'type': a['mimeType'].split('/')[1],
            'url': a['content'],
            'date': a['created']
        })

    return attachments_list


def attach_image_info(issue, images, access_token):

    for i in images:
        for a in issue['renderedFields']['attachment']:
            part = i['src'].split('attachment/')[1]
            part = part.split('/')[0]
            src = i['src'].replace(part + '_', '')
            if src in a['content']:
                i['url'] = a['content']
                if len(a['filename'].split('.')[0]) >= 80:
                    name = a['filename'].split('.')[0][:80] + '... .' + a['mimeType'].split('/')[1],
                else:
                    name = a['filename'].split('.')[0] + '.' + a['mimeType'].split('/')[1],
                i['name'] = name[0]
                i['type'] = a['mimeType'].split('/')[1],
                i['date'] = a['created']

    existing_images = []

    for i in images:
        existing_images.append(i['url'])

    ordered_images = []

    request_list = []

    for a in issue['renderedFields']['attachment']:
        if a['mimeType'].split('/')[1] in ['jpg', 'jpeg', 'png']:
            if a['content'] not in existing_images:
                value = {
                    'name': a['filename'].split('.')[0][:10] + '... .' + a['mimeType'].split('/')[1],
                    'image': None,
                    'type': a['mimeType'].split('/')[1],
                    'url': a['content'],
                    'date': a['created']
                }
                ordered_images.append(value)
                request_list.append(a)
            else:
                for i in images:
                    if i['url'] == a['content']:
                        ordered_images.append(i)

    pool = ThreadPool(10)
    result_images = pool.starmap(load_image, zip(request_list, repeat(access_token), repeat('True')))
    pool.close() 
    pool.join()

    for i in ordered_images:
        if i['image'] == None:
            for r in result_images:
                if i['content'] == r['content']:
                    i['image'] = r['image']

    return ordered_images


def save_settings(user, settings):

    us, _ = UserSettings.objects.update_or_create(
        user=user,
        defaults={
            'user': user,
            'issue_path': settings['issuePath'],
            'title': settings['title'],
            'description': settings['description'],
            'status': settings['status'],
            'attachments': settings['attachments'],
            'attachments_links': settings['attachmentsLinks'],
            'comments': settings['comments'],
            'users': settings['users'],
            'images': settings['images']
        }
    )
    return us


@csrf_exempt
@auth_required
def load_settings(request, client, claims, user):
    try:
        u, _ = UserSettings.objects.get_or_create(
            user=user,
            defaults={
                'user': user
            }
        )
        r = {
            'issuePath': u.issue_path,
            'title': u.title,
            'description': u.description,
            'status': u.status,
            'attachments': u.attachments,
            'attachmentsLinks': u.attachments_links,
            'comments': u.comments,
            'users': u.users,
            'images': u.images,
            'commentImages': u.comment_images,
            'custom': client.custom_template
        }
        return JsonResponse(r, status=200)
    except Exception as e:
        capture_exception(e)
    return JsonResponse({'message': 'error'}, status=500)


@csrf_exempt
@auth_required
def generate_pdf(request, client, claims, user):
    logging.basicConfig(filename='generate.log',format='%(asctime)s %(message)s')
    try:
        start_time = datetime.datetime.now()
        # Get user settings from request
        request_data = json.loads(request.body.decode('utf-8'))
        settings = request_data['content']

        save_settings(user, settings)

        # Get issue details from client's Jira instance
        issue, access_token = get_jira_issue(client, claims)

        after_issue = math.ceil((datetime.datetime.now() - start_time).total_seconds())

        # Replace issue image links with instance prefix
        base_url = client.base_url
        issue, images = replace_links(issue, base_url, access_token, settings)

        if settings['comments']:
            issue, comment_images = replace_comments_links(issue, base_url, access_token, settings)
            images.extend(comment_images)

        project_name = (base_url.split('https://')[1].split('.')[0]).replace('-', ' ')
        if settings['images']:
            images = attach_image_info(issue, images, access_token)
        else:
            images = []

        after_images = math.ceil((datetime.datetime.now() - start_time).total_seconds())

        attachments = build_attachments(issue, access_token)

        after_attachments = math.ceil((datetime.datetime.now() - start_time).total_seconds())
        
        # Build html file
        html = build_html(issue, settings, client.custom_template, attachments, images, project_name) #client.custom_template

        try:
            with open('/tmp/html/' + project_name.replace(' ', '-') + '-' + secrets.token_hex(16) + '-' + str(datetime.datetime.now()).replace(' ', '-') + '.html', 'w') as f:
                f.write(html)
        except Exception as e:
            capture_exception(e)
            pass

        after_build = math.ceil((datetime.datetime.now() - start_time).total_seconds())

        logging.error('Start building pdf')
        # Migrate HTML to PDF
        pdf_file = get_pdf(client, claims, html)
        logging.error('Finish building pdf')
        try:
            with open('/tmp/pdf/' + project_name.replace(' ', '-') + '-' + secrets.token_hex(16) + '-' + str(datetime.datetime.now()).replace(' ', '-') + '.pdf', 'wb') as f:
                f.write(pdf_file)
        except Exception as e:
            capture_exception(e)
            pass
        #pdf_file = True
        end_time = math.ceil((datetime.datetime.now() - start_time).total_seconds())
        end_size = math.ceil(sys.getsizeof(pdf_file) / 1024)
        try:
            Generation.objects.create(
                user=user,
                size_kb=end_size,
                time_seconds=end_time,
                time_issue=after_issue,
                time_images=after_images,
                time_attachments=after_attachments,
                time_build=after_build,
                images_sum=len(images)
            )
        except Exception as e:
            capture_exception(e)
            pass
        if pdf_file:
            print('got pdf file')
            # Return final pdf file to user
            return HttpResponse(pdf_file, status=200, content_type='application/pdf')
    except Exception as e:
        capture_exception(e)
        pass
    return JsonResponse({'message': 'error'}, status=500)
