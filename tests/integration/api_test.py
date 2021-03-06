# -*- coding: utf-8 -*-
from __future__ import print_function
from django.utils.encoding import force_text

from datetime import datetime, timedelta
import json
import pytest

from nav.models.fields import INFINITY
from nav.web.api.v1.views import get_endpoints


ENDPOINTS = { name:force_text(url) for name, url in get_endpoints().items() }


# Data for writable endpoints

TEST_DATA = {
    'account': {
        'login': 'testuser',
        'name': 'Test User',
        'accountgroups': [2, 3]
    },
    'location': {
        'id': 'Kulsås',
        'data': {'a': 'b'},
        'parent': 'mylocation',
        'description': 'ÆØÅ descr'
    },
    'netbox': {
        "ip": "158.38.152.169",
        "roomid": "myroom",
        "organizationid": "myorg",
        "categoryid": "SW",
        "snmp_version": 2
    },
    'room': {
        'id': 'blapp',
        'location': 'mylocation'
    }
}


# Generic tests

@pytest.mark.parametrize("url", ENDPOINTS.values())
def test_forbidden_endpoints(db, api_client, url):
    response = api_client.get(url)
    assert response.status_code == 403


@pytest.mark.parametrize("name, url", ENDPOINTS.items())
def test_allowed_endpoints(db, api_client, token, serializer_models, name, url):
    create_token_endpoint(token, name)
    if name in ['arp', 'cam']:
        # ARP and CAM wants filters
        response = api_client.get("{}?active=1".format(url))
    else:
        response = api_client.get(url)
    assert response.status_code == 200


@pytest.mark.parametrize("endpoint",
                         ['account', 'location', 'room'])
def test_delete(db, api_client, token, endpoint):
    create_token_endpoint(token, endpoint)
    response_create = create(api_client, endpoint, TEST_DATA.get(endpoint))
    res = json.loads(response_create.content.decode('utf-8'))
    response_delete = delete(api_client, endpoint, res.get('id'))
    response_get = get(api_client, endpoint, res.get('id'))

    print(response_delete)
    assert response_delete.status_code == 204

    print(response_get)
    assert response_get.status_code == 404


@pytest.mark.parametrize("endpoint",
                         ['account', 'netbox', 'location', 'room'])
def test_create(db, api_client, token, endpoint):
    create_token_endpoint(token, endpoint)
    response = create(api_client, endpoint, TEST_DATA.get(endpoint))
    print(response)
    assert response.status_code == 201


def test_page_size(db, api_client, token):
    endpoint = 'room'
    create_token_endpoint(token, endpoint)
    create(api_client, endpoint, {'id': 'blapp1', 'location': 'mylocation'})
    create(api_client, endpoint, {'id': 'blapp2', 'location': 'mylocation'})
    response = api_client.get('/api/1/room/?page_size=1')
    print(response.data)
    assert len(response.data.get('results')) == 1


# Account specific tests

def test_update_org_on_account(db, api_client, token):
    endpoint = 'account'
    create_token_endpoint(token, endpoint)
    data = {"organizations": ["myorg"]}
    response = update(api_client, endpoint, 1, data)
    print(response)
    assert response.status_code == 200

    data = {"organizations": []}
    response = update(api_client, endpoint, 1, data)
    print(response)
    assert response.status_code == 200


def test_update_group_on_org(db, api_client, token):
    endpoint = 'account'
    create_token_endpoint(token, endpoint)
    # Only admin group
    data = {"accountgroups": [1]}
    response = update(api_client, endpoint, 1, data)
    print(response)
    assert response.status_code == 200


# Netbox specific tests

def test_update_netbox(db, api_client, token):
    endpoint = 'netbox'
    create_token_endpoint(token, endpoint)
    response_create = create(api_client, endpoint, TEST_DATA.get(endpoint))
    res = json.loads(response_create.content.decode('utf-8'))
    data = {'categoryid': 'GW'}
    response_update = update(api_client, endpoint, res['id'], data)
    print(response_update)
    assert response_update.status_code == 200


def test_delete_netbox(db, api_client, token):
    endpoint = 'netbox'
    create_token_endpoint(token, endpoint)
    response_create = create(api_client, endpoint, TEST_DATA.get(endpoint))
    json_create = json.loads(response_create.content.decode('utf-8'))
    response_delete = delete(api_client, endpoint, json_create['id'])
    response_get = get(api_client, endpoint, json_create['id'])
    json_get = json.loads(response_get.content.decode('utf-8'))

    print(response_delete)
    print(json_get['deleted_at'])

    assert response_delete.status_code == 204
    assert json_get['deleted_at'] != None


# Room specific tests


def test_get_wrong_room(db, api_client, token):
    create_token_endpoint(token, 'room')
    response = api_client.get('{}blapp/'.format(ENDPOINTS['room']))
    print(response)
    assert response.status_code == 404


def test_get_new_room(db, api_client, token):
    endpoint = 'room'
    create_token_endpoint(token, endpoint)
    create(api_client, endpoint, TEST_DATA.get(endpoint))
    response = api_client.get('/api/1/room/blapp/')
    print(response)
    assert response.status_code == 200


def test_patch_room_not_found(db, api_client, token):
    create_token_endpoint(token, 'room')
    data = {'location': 'mylocation'}
    response = api_client.patch('/api/1/room/blapp/', data, format='json')
    print(response)
    assert response.status_code == 404


def test_patch_room_wrong_location(db, api_client, token):
    endpoint = 'room'
    create_token_endpoint(token, endpoint)
    create(api_client, endpoint, TEST_DATA.get(endpoint))
    data = {'location': 'mylocatio'}
    response = api_client.patch('/api/1/room/blapp/', data, format='json')
    print(response)
    assert response.status_code == 400


def test_patch_room(db, api_client, token):
    endpoint = 'room'
    create_token_endpoint(token, 'room')
    create(api_client, endpoint, TEST_DATA.get(endpoint))
    data = {'location': 'mylocation'}
    response = api_client.patch('/api/1/room/blapp/', data, format='json')

    print(response)
    assert response.status_code == 200


def test_delete_room_wrong_room(db, api_client, token):
    endpoint = 'room'
    create_token_endpoint(token, 'room')
    create(api_client, endpoint, TEST_DATA.get(endpoint))
    response = api_client.delete('/api/1/room/blap/')

    print(response)
    assert response.status_code == 404


# Helpers

def create_token_endpoint(token, name):
    token.endpoints = {name: ENDPOINTS.get(name)}
    token.save()


def get(api_client, endpoint, id=None):
    endpoint = ENDPOINTS[endpoint]
    if id:
        endpoint = endpoint + force_text(id) + '/'
    return api_client.get(endpoint)


def create(api_client, endpoint, data):
    """Sends a post request to endpoint with data"""
    return api_client.post(ENDPOINTS[endpoint], data, format='json')


def update(api_client, endpoint, id, data):
    """Sends a patch request to endpoint with data"""
    return api_client.patch(ENDPOINTS[endpoint] + force_text(id) + '/', data, format='json')


def delete(api_client, endpoint, id):
    """Sends a delete request to endpoint"""
    return api_client.delete(ENDPOINTS[endpoint] + force_text(id) + '/')


# Fixtures

@pytest.fixture()
def serializer_models():
    """Fixture for testing API serializers

    - unrecognized_neighbor
    - auditlog
    """
    from nav.models import cabling, event, manage, profiles, rack
    from nav.auditlog import models as auditlog
    netbox = manage.Netbox(ip='127.0.0.1', sysname='localhost.example.org',
                           organization_id='myorg', room_id='myroom', category_id='SRV',
                           read_only='public', snmp_version=2)

    netbox.save()

    group = manage.NetboxGroup.objects.all()[0]
    manage.NetboxCategory(netbox=netbox, category=group).save()

    interface = manage.Interface(netbox=netbox, ifindex=1, ifname='if1',
                                 ifdescr='ifdescr', iftype=1, speed=10)
    interface.save()
    manage.Cam(sysname='asd', mac='aa:aa:aa:aa:aa:aa', ifindex=1,
               end_time=datetime.now()).save()
    manage.Arp(sysname='asd', mac='aa:bb:cc:dd:ee:ff', ip='123.123.123.123',
               end_time=datetime.now()).save()
    manage.Prefix(net_address='123.123.123.123').save()
    manage.Vlan(vlan=10, net_type_id='lan').save()
    rack.Rack(room_id='myroom').save()
    cabel = cabling.Cabling(room_id='myroom', jack='1')
    cabel.save()
    cabling.Patch(interface=interface, cabling=cabel).save()

    source = event.Subsystem.objects.get(pk='pping')
    target = event.Subsystem.objects.get(pk='eventEngine')
    event_type = event.EventType.objects.get(pk='boxState')

    boxdown_id = 3

    event.EventQueue(source=source, target=target, event_type=event_type, netbox=netbox).save()
    event.AlertHistory(source=source, event_type=event_type, netbox=netbox,
                       start_time=datetime.now() - timedelta(days=1),
                       value=1, severity=50,
                       alert_type_id=boxdown_id,
                       end_time=INFINITY).save()
    admin = profiles.Account.objects.get(login='admin')
    auditlog.LogEntry.add_log_entry(admin, verb='verb', template='asd')
