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


from django.contrib.auth.middleware import RemoteUserMiddleware
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.contrib import auth

from placard.client import LDAPClient


class LDAPRemoteUserMiddleware(RemoteUserMiddleware):
    """
    Middleware for utilizing web-server-provided authentication.
    
    If request.user is not authenticated, then this middleware attempts to
    authenticate the username passed in the ``REMOTE_USER`` request header.
    If authentication is successful, the user is automatically logged in to
    persist the user in the session. 

    If the user doesn't exist the middleware will create a new User object 
    based on information pulled from LDAP
    """

    def process_request(self, request):
        # AuthenticationMiddleware is required so that request.user exists.
        if not hasattr(request, 'user'):
            raise ImproperlyConfigured(
                "The placard remote LDAP user auth middleware requires the"
                " authentication middleware to be installed.  Edit your"
                " MIDDLEWARE_CLASSES setting to insert"
                " 'django.contrib.auth.middleware.AuthenticationMiddleware'"
                " before the RemoteUserMiddleware class.")
        try:
            username = request.META[self.header]
        except KeyError:
            # If specified header doesn't exist then return (leaving
            # request.user set to AnonymousUser by the
            # AuthenticationMiddleware).
            return
        # If the user is already authenticated and that user is the user we are
        # getting passed in the headers, then the correct user is already
        # persisted in the session and we don't need to continue.
        if request.user.is_authenticated():
            if request.user.username == self.clean_username(username, request):
                return
        # We are seeing this user for the first time in this session, attempt
        # to authenticate the user.
        try:
            user = User.objects.get(username__exact=username)
        except User.DoesNotExist:
            # Create user
            conn = LDAPClient()
            ldap_user = conn.get_user("uid=%s" % username)
            user = User.objects.create_user(ldap_user.uid, ldap_user.mail)
            try:
                user.first_name = ldap_user.givenName
            except AttributeError:
                pass
            try:
                user.last_name = ldap_user.sn
            except AttributeError:
                pass
            user.save()
    
        # User is valid.  Set request.user and persist user in the session
        # by logging the user in.
        request.user = user
        auth.login(request, user)


