"""Contacts URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url

from contact import views

urlpatterns = [
    url(r'^$', views.login),
    url(r'^logout/$', views.logout, name="logout"),

    url(r'^search/$', views.search_contact, name="search"),
    url(r'^bulk-search/$', views.bulk_search, name="bulk-search"),
    url(r'^yahoo-search/$', views.yahoo_search, name="yahoo-search"),
    url(r'^get-data/$', views.get_data, name="get-data"),

    url(r'^download-zip/$', views.getfiles, name="download-zip"),

    url(r'^upload-file/$', views.uploadfile, name="upload-file"),
    url(r'^upload-yahoo/$', views.uploadyahoo, name="upload-yahoo")
]
