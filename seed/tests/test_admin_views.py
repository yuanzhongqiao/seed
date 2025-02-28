# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from seed.lib.superperms.orgs.models import (
    ROLE_OWNER,
    Organization,
    OrganizationUser
)
from seed.utils.organizations import create_organization

# Custom user model compatibility
User = get_user_model()


class AdminViewsTest(TestCase):

    def setUp(self):
        admin_user_details = {'username': 'admin@testserver',
                              'email': 'admin@testserver',
                              'password': 'admin_passS1'}
        self.admin_user = User.objects.create_superuser(**admin_user_details)
        self.client.login(**admin_user_details)

        user_details = {'username': 'testuser@testserver',
                        'email': 'testuser@testserver',
                        'password': 'user_passS1'}
        self.user = User.objects.create_user(**user_details)

        # for some reason we can't reverse api:v3:organizations-create
        # so we use -list b/c it's the same url but with different HTTP method
        self.add_org_url = reverse_lazy('api:v3:organizations-list')
        self.add_user_url = reverse_lazy('api:v3:user-list')

    def _post_json(self, url, data):
        """
        Handles posting a python object as json to a given url.
        """
        data_json = json.dumps(data)
        res = self.client.post(url,
                               data_json,
                               content_type='application/json')
        res.body = json.loads(res.content)
        return res

    def _is_org_owner(self, user, org):
        """
        Tests whether a given user is the owner of an org.
        Handles traversing the somewhat ugly org object relationships.
        """
        return OrganizationUser.objects.filter(
            organization=org, user=user, role_level=ROLE_OWNER
        ).exists()

    def test_add_org(self):
        """
        Happy path test for creating a new org.
        """
        data = {'user_id': self.admin_user.pk,
                'organization_name': 'New Org'}
        res = self._post_json(self.add_org_url, data)

        self.assertEqual(res.body['status'], 'success')
        self.assertEqual(Organization.objects.count(), 1)

        new_org = Organization.objects.first()
        self.assertTrue(self._is_org_owner(self.admin_user, new_org))
        self.assertEqual(new_org.name, data['organization_name'])

    def test_add_org_dupe(self):
        """
        Trying to create an org with a dupe name fails.
        """
        create_organization(user=self.admin_user, org_name='Orgname')
        data = {
            'user_id': self.user.pk,
            'organization_name': 'Orgname'
        }

        res = self._post_json(self.add_org_url, data)

        self.assertEqual(res.body['status'], 'error')
        self.assertEqual(Organization.objects.count(), 1)

        # and most importantly, the admin/owner of the org did not change
        org = Organization.objects.first()
        self.assertTrue(self._is_org_owner(self.admin_user, org))

    def test_add_user_existing_org(self):
        """
        Test creating a new user, adding them to an existing org
        in the process.
        """
        org, org_user, _user_created = create_organization(
            self.admin_user, name='Existing Org'
        )
        data = {
            'first_name': 'New',
            'last_name': 'User',
            'email': 'new_user@testserver',
            'role_level': 'ROLE_MEMBER'
        }

        res = self._post_json(self.add_user_url + f'?organization_id={org.pk}', data)
        self.assertEqual(res.body['status'], 'success')
        user = User.objects.get(username=data['email'])
        self.assertEqual(user.email, data['email'])

        # the user should be a member of the existing org
        self.assertTrue(user in org.users.all())

        # Since this is the only user, it's automatically the owner.
        self.assertTrue(self._is_org_owner(self.admin_user, org))
        self.assertEqual(Organization.objects.count(), 1)

    def test_add_user_new_org(self):
        """
        Create a new user and a new org at the same time.
        """
        org, _, _ = create_organization(self.user, "test-organization-a")
        data = {'org_name': 'New Org',
                'first_name': 'New',
                'last_name': 'Owner',
                'organization_id': org.id,
                'email': 'new_owner@testserver'}
        res = self._post_json(self.add_user_url, data)

        self.assertEqual(res.body['status'], 'success')
        user = User.objects.get(username=data['email'])
        self.assertEqual(user.email, data['email'])

        # new user should be member, admin and owner of new org
        org = Organization.objects.get(name='New Org')
        self.assertTrue(user in org.users.all())
        self.assertTrue(self._is_org_owner(user, org))

    def test_add_user_no_org(self):
        """
        Should not be able to create a new user without either
        selecting or creating an org at the same time.
        """
        data = {'first_name': 'New',
                'last_name': 'User',
                'email': 'bad_user@testserver'}
        res = self._post_json(self.add_user_url, data)
        self.assertEqual(res.body['status'], 'error')

        self.assertFalse(User.objects.filter(username=data['email']).exists())
        self.assertFalse(User.objects.filter(email=data['email']).exists())

    def test_signup_process(self):
        """
        Simulates the entire new user signup process, from initial
        account creation by an admin to receiving the signup email
        to confirming the account and setting a password.
        """
        org, _, _ = create_organization(self.user, "test-organization-a")
        data = {'first_name': 'New',
                'last_name': 'User',
                'email': 'new_user@testserver',
                'organization_id': org.id,
                'org_name': 'New Org'}
        res = self._post_json(self.add_user_url, data)
        self.client.logout()  # stop being the admin user
        self.assertEqual(res.body['status'], 'success')  # to help debug fails

        user = User.objects.get(email=data['email'])

        # user's password does not work yet
        self.assertFalse(user.has_usable_password())

        token = default_token_generator.make_token(user)
        signup_url = reverse("landing:signup", kwargs={
            'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
            "token": token
        })

        # make sure we sent an email to the right address
        # and it contains the signup url
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertTrue(signup_url in msg.body)
        self.assertTrue(data['email'] in msg.to)

        # actually go to that url to make sure it works
        res = self.client.get(signup_url)
        self.assertEqual(res.status_code, 302)

        # post the new password
        password_post = {'new_password1': 'newpassS2',
                         'new_password2': 'newpassS2'}

        set_password_url = reverse("landing:signup", kwargs={
            'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
            "token": 'set-password'
        })
        res = self.client.post(set_password_url, data=password_post)

        # reload the user
        user = User.objects.get(pk=user.pk)

        # user is now has a working password
        self.assertTrue(user.has_usable_password())

    def test_signup_process_force_lowercase_email(self):
        """
        Simulates the signup and login forcing login username to lowercase
        """
        org, _, _ = create_organization(self.user, "test-organization-a")
        data = {'first_name': 'New',
                'last_name': 'User',
                'email': 'New_Lower_User@testserver.com',
                'organization_id': org.id,
                'org_name': 'New Org'}
        res = self._post_json(self.add_user_url, data)
        self.client.logout()  # stop being the admin user
        self.assertEqual(res.body['status'], 'success')  # to help debug fails

        user = User.objects.get(email=data['email'])

        # user's password does not work yet
        self.assertFalse(user.has_usable_password())

        token = default_token_generator.make_token(user)
        signup_url = reverse("landing:signup", kwargs={
            'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
            "token": token
        })

        # make sure we sent an email to the right address
        # and it contains the signup url
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertTrue(signup_url in msg.body)
        self.assertTrue(data['email'] in msg.to)

        # Follow link to be redirected to new password page
        res = self.client.get(signup_url, data)
        self.assertEqual(res.status_code, 302)

        # post the new password
        password_post = {'new_password1': 'newpassS3',
                         'new_password2': 'newpassS3'}

        set_password_url = reverse("landing:signup", kwargs={
            'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
            "token": 'set-password'
        })
        res = self.client.post(set_password_url, data=password_post)

        # reload the user
        user = User.objects.get(pk=user.pk)
        # user is now has a working password and lowercase username
        self.assertTrue(user.has_usable_password())
        self.assertEqual(user.email, data['email'])
        self.assertEqual(user.username, data['email'].lower())

        # test that login works
        resp = self.client.post(
            reverse('landing:login'),
            {'email': data['email'], 'password': 'newpassS3'}
        )
        # good logins will have 302 and no content
        user = User.objects.get(pk=user.pk)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.content, b'')
