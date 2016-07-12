from django.shortcuts import render_to_response, redirect
from contact.models import *
from django.template import RequestContext

from py_bing_search import PyBingWebSearch

from functools import wraps
from Contacts import settings
import random, string, os

import time
import json
import StringIO
import shutil
import datetime

from django.http import HttpResponse

from django.views.decorators.csrf import csrf_exempt

# Login Required decorator
def login_required():
    def login_decorator(function):
        @wraps(function)
        def wrapped_function(request):

            # if a user is not authorized, redirect to login page
            if 'user' not in request.session or request.session['user'] is None:
                return redirect("/")
            # otherwise, go on the request
            else:
                return function(request)

        return wrapped_function

    return login_decorator


# login view
def login(request):
    error = 'none'

    if 'username' in request.POST:

        # get username and password from request.
        username = request.POST['username']
        password = request.POST['password']

        # get a user from database based on username and password
        user = User.objects.filter(username=username, password=password)

        # check whether the user is in database or not
        if len(user) < 1:
            error = 'block'
        else:
            request.session['user'] = {
                "id": user[0].id,
                "username": user[0].username,
            }

            return redirect("/search")

    return render_to_response('login.html', {'error':error}, context_instance=RequestContext(request))


# logout view
#   initialize session variable
def logout(request):
    request.session['user'] = None
    return redirect("/")


@login_required()
def search_contact(request):

    return render_to_response('contact/input.html', locals(), context_instance=RequestContext(request))


@login_required()
def bulk_search(request):

    return render_to_response('contact/bulkInput.html', locals(), context_instance=RequestContext(request))


@login_required()
def get_data(request):
    data = dict()

    # get data from user
    data['siteid'] = getValue(request.GET, 'siteid')
    data['name'] = getValue(request.GET, 'name')
    data['title'] = getValue(request.GET, 'title')
    data['company'] = getValue(request.GET, 'company')
    data['location'] = getValue(request.GET, 'location')
    data['site'] = getValue(request.GET, 'site')

    lines = _getData(data)

    # create csv file in static/data/
    #if folder does not exist, create it
    filename = "data_%s.csv" % random_word(10)
    if not os.path.exists(os.path.join(settings.BASE_DIR, 'contact/static/data')):
        os.makedirs(os.path.join(settings.BASE_DIR, 'contact/static/data'))

    # open file
    filepath = "%s/%s" % (os.path.join(settings.BASE_DIR, 'contact/static/data'), filename)
    fp = open(filepath, "wb")

    title = '"Input Siteid","Input Company","Input Title","Input Location","First Name","Last Name","Title",' + \
            '"Company","Location","Location Full","Industry","linkedinurl","Current Company","Education","Date",' + \
            '"Score","Location_Match","Company_Match","Description"\n'
    fp.write(title)

    fp.write(''.join(lines))
    # print(res)

    return HttpResponse(filename)

@login_required()
@csrf_exempt
def getfiles(request):
    # Files (local path) to put in the .zip
    # FIXME: Change this (get paths from DB etc)
    if 'filename' in request.POST:
        filename = request.POST['filename']
    else:
        redirect("/login")

    path = os.path.join(settings.BASE_DIR, 'contact/static/data/' + filename)

    # Open StringIO to grab in-memory ZIP contents
    s = StringIO.StringIO()

    with open(path, "r") as fp:
        s.write(fp.read())

    # Grab ZIP file from in-memory, make response with correct MIME-type
    resp = HttpResponse(s.getvalue(), content_type="text/csv")
    # ..and correct content-disposition
    if 'bulkinput' in filename:
        temp = "Bulk_Contact_Search_%s.csv" % datetime.datetime.now().strftime('%d%m%Y')
    else:
        temp = "Company_%s.csv" % datetime.datetime.now().strftime('%d%m%Y')
    resp['Content-Disposition'] = "attachment; filename=" + temp

    if not os.path.exists(os.path.join(settings.BASE_DIR, 'contact/static/data/' + filename)):
        os.remove(os.path.join(settings.BASE_DIR, 'contact/static/data/' + filename))

    return resp

@login_required()
@csrf_exempt
def uploadfile(request):

    if 'files[]' in request.FILES:
        # get file from user
        uploaded_file = request.FILES['files[]']

        filename = "bulkinput_%s.csv" % random_word(10)
        if not os.path.exists(os.path.join(settings.BASE_DIR, 'contact/static/data')):
            os.makedirs(os.path.join(settings.BASE_DIR, 'contact/static/data'))

        # open file
        filepath = "%s/%s" % (os.path.join(settings.BASE_DIR, 'contact/static/data'), filename)
        fp = open(filepath, "wb")

        title = '"Input Siteid","Input Company","Input Title","Input Location","First Name","Last Name","Title",' + \
            '"Company","Location","Location Full","Industry","linkedinurl","Current Company","Education","Date",' + \
            '"Score","Location_Match","Company_Match","Description"\n'
        fp.write(title)

        res = ""
        for chunk in uploaded_file.chunks():
            tokens = chunk.split("\n")
            for token in tokens:
                data = dict()
                token = token.replace("\r", "")
                temp = token.split(",")
                if len(temp) > 6:
                    # get data from file
                    data['siteid'] = temp[0]
                    data['name'] = temp[1].replace("\"", "") + " " + temp[2].replace("\"", "")
                    data['name'] = data['name'].strip()
                    data['title'] = temp[3].replace("\"", "")
                    data['company'] = temp[4].replace("\"", "")
                    data['location'] = temp[5].replace("\"", "")
                    data['site'] = temp[6].replace("\"", "")

                    lines = _getData(data)
                    fp.write("".join(lines))
    res = {"filename": filename}

    return HttpResponse(json.dumps(res))


def random_word(length):
   return ''.join(random.choice(string.lowercase + string.uppercase + string.digits) for i in range(length))


def getValue(data, key):
    if key not in data:
        return u""
    else:
        return data[key]

def _getData(data, name=1):
    srch_title = ""
    if data['title'] != u"":
        srch_title = "\"%s\"" % data['title']

    if data['site'] == u"":
        data['site'] = "www.linkedin.com/in/"

    com_name = data["company"]
    if com_name != "":
        com_name = "Current: %s" % com_name

    srch_location = ""
    if data['location'] != u"":
        srch_location = "Location %s" % data['location']

    search_term = "site:%s %s %s %s" % (data['site'], com_name, srch_title, srch_location)
    print search_term

    # get data using bing api
    bing_web = PyBingWebSearch(settings.BING_API_KEY, search_term.strip())
    result = bing_web.search_all(limit=100, format='json') #1-50


    name_tp = data['name'].split(" ")
    first_name = name_tp[0]
    last_name = ""
    if(len(name_tp) > 1):
        last_name = name_tp[1]

    res = []

    index = 0
    for item in result:
        index += 1
        '''title_tp = item.title
        if title != u"":
            title_tp = title'''
        description = item.description.replace(",", " ")
        description = description.replace("\"", " ")

        if "| LinkedIn" in item.title:
            temp = item.title
            temp = temp.split("|")[0].strip().split(" ")
            first_name = temp[0]
            last_name = temp[-1]
            item.title = ""

        if name == 0:
            first_name = ""
            last_name = ""

        # get title and company from a search result.
        ps_des = parse_str(description)
        res_company = ""
        if ps_des is not None:
            res_company = ps_des[1].strip()
            item.title = ps_des[0].strip()

        # get location and industry from a result
        res_location = ""
        industry_str = ""
        ps_ind = parse_str(description, "Industry")
        if ps_ind is not None:
            res_location = ps_ind[0].replace("Location", "").strip()
            industry_str = ps_ind[1].strip()

        # get score of location
        full_location = res_location
        res_location = res_location.replace("Area", "")
        res_location = res_location.replace("Industry", "")
        res_location = res_location.replace("Greater", "").strip()

        score_location = "No"
        if res_location != "" and (res_location == data['location'] or res_location in data['location'] or data['location'] in res_location):
            score_location = "Yes"

        # get score of company
        score_company = "No"
        if res_company != "" and res_company == data['company'] and res_company:
            score_company = "Yes"


        # get score
        score = 3
        if index < 4:
            score = 1
        elif index < 6:
            score = 2

        # get current company
        curr_com = parse_curr_company(description)

        # get education
        education = parse_curr_company(description, "Education:")

        # get date and timestamp
        time_stamp = time.time()
        date = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')

        if data['name'] == "" or (data['name'] != "" and data['name'] == "%s %s" % (first_name, last_name)):
            line = '"%s","%s","%s","%s","%s","%s","%s","%s","%s","%s","%s","%s","%s","%s","%s","%d","%s","%s","%s"\n' % \
                   (data['siteid'], data['company'], data['title'], data['location'], first_name, last_name, item.title, \
                    res_company, res_location, full_location, industry_str, item.url, curr_com, education, date, \
                    score, score_location, score_company, description)

            line = line.encode("utf8")
            line = line.replace("\u00E2\u20AC\u2122", "")
            res.append(line)

    return res


def parse_str(str, key=" at "):
    index_title = str.find(" at ")
    index_location = str.find("Location")
    index_industry = str.find("Industry")

    if index_title != -1:

        if index_industry != -1:
            if key == " at " and (index_title > index_location or index_title > index_industry):
                return None
        else:
            if key == " at " and index_location == -1:
                return None
            if key == " at " and index_title > index_location:
                return None
    '''else:
        if index_location == -1 or index_industry == -1 and index_industry > index_location:
            return None'''

    str_list = str.split(".")

    str_list = [item.strip() for item in str_list if item != ""]

    for item in str_list:

        res = item.split(key)
        if len(item) > 0 and key in item:

            if len(res) > 1:
                index = str_list.index(item)
                if "Previous:" in item or "Education:" in item:
                    continue

                if index > 1 and ("Previous:" in str_list[index - 1].strip() or "Education:" in str_list[index - 1].strip()):
                    continue

                for i in range(0, index + 1):
                    if "Current:" in str_list[i].strip():
                        res[0] = ""


                return [res[0].split("Location")[-1], res[1]]
            else:
                return ["", res[0]]

        elif key == "Industry" and len(res) == 1:

            if "Location" in res[0]:
                index = str_list.index(item)
                temp = [res[0].split("Location")[-1], ""]

                if len(str_list) > index + 1 and "Industry" in str_list[index + 1]:
                    temp[1] = str_list[index + 1]
                return temp

    return None


def parse_curr_company(str, key="Current:"):
    str_list = str.split(".")

    for item in str_list:
        item = item.strip()
        if key in item and len(item.split(key)) > 1:
            res = item.split(key)[1].strip()
            res = res.split(";")[0]

            return res

    return ""
