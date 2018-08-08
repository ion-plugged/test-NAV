# -*- coding: utf-8 -*-
#
# This file is part of Network Administration Visualized (NAV).
#
# NAV is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License version 2 as published by the Free
# Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.  You should have received a copy of the GNU General Public
# License along with NAV. If not, see <http://www.gnu.org/licenses/>.
#
"""
Test report generators for basic errors.

These tests simply enumerate all known reports and ensure that the dbresult is
error free. This only ensures that the SQL can be run, no further verification
is performed.
"""
from __future__ import unicode_literals
import os.path
import pytest

from django.http import QueryDict
from django.core.urlresolvers import reverse

from nav import db
from nav.report.generator import ReportList, Generator
from nav.buildconf import sysconfdir

config_file = os.path.join(sysconfdir, 'report', 'report.conf')
config_file_local = os.path.join(sysconfdir, 'report', 'report.local.conf')


def report_list():
    result = ReportList(config_file)
    return [report[0] for report in result.reports]


@pytest.mark.parametrize("report_name", report_list())
def test_report(report_name):
    #uri = 'http://example.com/report/%s/' % report_name
    uri = QueryDict('').copy()
    db.closeConnections() # Ensure clean connection for each test

    generator = Generator()
    report, contents, neg, operator, adv, config, dbresult = generator.make_report(
        report_name, config_file, config_file_local, uri, None, None)

    assert dbresult, 'dbresult is None'
    assert not dbresult.error, dbresult.error + '\n' + dbresult.sql


def test_non_ascii_filter_should_work(client):
    url = reverse('report-by-name', kwargs={'report_name': 'room'})
    url = "{}?roomid=æøå".format(url)
    response = client.get(url, follow=True)
    assert response.status_code == 200
