#!/usr/bin/python

# Copyright 2010 VPAC
#
# This file is part of django-placard.
#
# django-placard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# django-placard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with django-placard  If not, see <http://www.gnu.org/licenses/>.


from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.test import TestCase

import unittest

from tldap.test import slapd
from tldap.test.data import test_ldif

import placard.ldap_bonds as bonds


class UserViewsTests(TestCase):

    def setUp(self):
        server = slapd.Slapd()
        server.set_port(38911)
        server.start()

        server.ldapadd("\n".join(test_ldif)+"\n")

        self.server = server

        super_user = User.objects.create_user('super', 'sam@vpac.org', 'aq12ws')
        super_user.is_superuser = True
        super_user.save()

    def tearDown(self):
        self.server.stop()

    def test_account_list(self):
        response = self.client.get(reverse('plac_account_list'))
        self.failUnlessEqual(response.status_code, 200)

    def test_account_detail(self):
        response = self.client.get(reverse('plac_account_detail', args=['testuser1']))
        self.failUnlessEqual(response.status_code, 200)
        response = self.client.get(reverse('plac_account_detail', args=['nousers']))
        self.failUnlessEqual(response.status_code, 404)

    def test_delete_view(self):
        response = self.client.get(reverse('plac_account_delete', args=['testuser1']))
        self.failUnlessEqual(response.status_code, 302)
        self.client.login(username='super', password='aq12ws')
        response = self.client.get(reverse('plac_account_delete', args=['testuser1']))
        self.failUnlessEqual(response.status_code, 200)

    def test_account_verbose(self):
        response = self.client.get(reverse('plac_account_detail_verbose', args=['testuser2']))
        self.failUnlessEqual(response.status_code, 200)
        self.client.login(username='super', password='aq12ws')
        response = self.client.get(reverse('plac_account_detail_verbose', args=['testuser2']))
        self.failUnlessEqual(response.status_code, 200)

    def test_lock_account_view(self):
        self.client.get(reverse('plac_account_detail_verbose', args=['testuser2']))

    def test_lock_unlock_account_view(self):
        account = bonds.master.accounts().get(uid='testuser2')
        account.change_password('qwerty')
        account.save()

        account = bonds.master.accounts().get(uid='testuser2')
        self.failUnlessEqual(account.is_locked(), False)
        self.failUnlessEqual(account.check_password('aq12ws'), False)
        self.failUnlessEqual(account.check_password('qwerty'), True)

        self.client.login(username='super', password='aq12ws')
        self.client.post(reverse('plac_lock_user', args=['testuser2']))

        account = bonds.master.accounts().get(uid='testuser2')
        self.failUnlessEqual(account.is_locked(), True)
        self.failUnlessEqual(account.check_password('aq12ws'), False)
        self.failUnlessEqual(account.check_password('qwerty'), False)

        self.client.post(reverse('plac_unlock_user', args=['testuser2']))

        account = bonds.master.accounts().get(uid='testuser2')
        self.failUnlessEqual(account.is_locked(), False)
        self.failUnlessEqual(account.check_password('aq12ws'), False)
        self.failUnlessEqual(account.check_password('qwerty'), True)


class PasswordTests(TestCase):

    def setUp(self):
        global server
        server = slapd.Slapd()
        server.set_port(38911)
        server.start()

        server.ldapadd("\n".join(test_ldif)+"\n")

        self.server = server

        super_user = User.objects.create_user('super', 'sam@vpac.org', 'aq12ws')
        super_user.is_superuser = True
        super_user.save()

    def tearDown(self):
        self.server.stop()

    def test_api(self):
        u = bonds.master.accounts().get(uid='testuser2')
        u.change_password('aq12ws')
        u.save()

        self.failUnlessEqual(u.check_password('aq12ws'), True)
        self.failUnlessEqual(u.check_password('qwerty'), False)

        u = bonds.master.accounts().get(uid='testuser3')
        u.change_password('qwerty')
        u.save()

        self.failUnlessEqual(u.check_password('aq12ws'), False)
        self.failUnlessEqual(u.check_password('qwerty'), True)

    def test_admin_view(self):
        response = self.client.get(reverse('plac_account_password', args=['testuser1']))
        self.failUnlessEqual(response.status_code, 302)
        self.client.login(username='super', password='aq12ws')
        response = self.client.get(reverse('plac_account_password', args=['testuser1']))
        self.failUnlessEqual(response.status_code, 200)

        response = self.client.post(reverse('plac_account_password', args=['testuser1']), {'new1': 'aq12ws222', 'new2': 'aq12ws222'})
        self.failUnlessEqual(response.status_code, 302)

        u = bonds.master.accounts().get(uid='testuser1')
        self.failUnlessEqual(u.check_password('aq12ws222'), True)

    def test_account_view(self):
        u = bonds.master.accounts().get(uid='testuser2')
        u.change_password('aq12ws')
        u.save()

        luser = bonds.master.accounts().get(uid='testuser2')
        User.objects.create_user(luser.uid, luser.mail, 'aq12ws')

        response = self.client.get(reverse('plac_password'))
        self.failUnlessEqual(response.status_code, 302)

        self.client.login(username='testuser2', password='aq12ws')

        response = self.client.get(reverse('plac_account_password', args=['testuser1']))
        self.failUnlessEqual(response.status_code, 403)

        response = self.client.get(reverse('plac_password'))
        self.failUnlessEqual(response.status_code, 200)

        response = self.client.post(reverse('plac_password'), {'old': 'aq12ws', 'new1': 'aq12ws222', 'new2': 'aq12ws222'})
        self.failUnlessEqual(response.status_code, 302)

        self.failUnlessEqual(u.check_password('aq12ws222'), True)

if __name__ == '__main__':
    unittest.main()
