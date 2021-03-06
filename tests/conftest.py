from contextlib import contextmanager
import os
from datetime import date, datetime, timedelta
from unittest.mock import Mock

import pytest
from notifications_python_client.errors import HTTPError
from flask import url_for
from bs4 import BeautifulSoup

from app import create_app
from app.notify_client.models import (
    User,
    InvitedUser
)


from . import (
    service_json,
    TestClient,
    template_json,
    template_version_json,
    api_key_json,
    job_json,
    notification_json,
    invite_json,
    sample_uuid,
    generate_uuid,
    single_notification_json
)


@pytest.fixture(scope='session')
def app_(request):
    app = create_app()

    ctx = app.app_context()
    ctx.push()

    def teardown():
        ctx.pop()

    request.addfinalizer(teardown)
    app.test_client_class = TestClient
    return app


@pytest.fixture(scope='function')
def service_one(api_user_active):
    return service_json(SERVICE_ONE_ID, 'service one', [api_user_active.id])


@pytest.fixture(scope='function')
def service_with_reply_to_addresses(api_user_active):
    return service_json(
        SERVICE_ONE_ID,
        'service one',
        [api_user_active.id],
        reply_to_email_address='test@example.com',
        sms_sender='elevenchars',
    )


@pytest.fixture(scope='function')
def fake_uuid():
    return sample_uuid()


@pytest.fixture(scope='function')
def mock_get_service(mocker, api_user_active):
    def _get(service_id):
        service = service_json(service_id, users=[api_user_active.id], message_limit=50)
        return {'data': service}

    return mocker.patch('app.service_api_client.get_service', side_effect=_get)


@pytest.fixture(scope='function')
def mock_get_international_service(mocker, api_user_active):
    def _get(service_id):
        service = service_json(service_id, users=[api_user_active.id], permissions=['sms', 'international_sms'])
        return {'data': service}

    return mocker.patch('app.service_api_client.get_service', side_effect=_get)


@pytest.fixture(scope='function')
def mock_get_detailed_service(mocker, api_user_active):
    def _get(service_id):
        return {
            'data': {
                'id': service_id,
                'free_sms_fragment_limit': 250000,
                'statistics': {
                    'email': {'requested': 0, 'delivered': 0, 'failed': 0},
                    'sms': {'requested': 0, 'delivered': 0, 'failed': 0}
                },
                'created_at': str(datetime.utcnow())
            }
        }

    return mocker.patch('app.service_api_client.get_detailed_service', side_effect=_get)


@pytest.fixture(scope='function')
def mock_get_detailed_service_for_today(mocker, api_user_active):
    def _get(service_id):
        return {
            'data': {
                'id': service_id,
                'free_sms_fragment_limit': 250000,
                'statistics': {
                    'email': {'requested': 0, 'delivered': 0, 'failed': 0},
                    'sms': {'requested': 0, 'delivered': 0, 'failed': 0}
                }
            }
        }

    return mocker.patch('app.service_api_client.get_detailed_service_for_today', side_effect=_get)


@pytest.fixture(scope='function')
def mock_get_detailed_services(mocker, fake_uuid):
    service_one = service_json(
        id_=SERVICE_ONE_ID,
        name="service_one",
        users=[fake_uuid],
        message_limit=1000,
        active=True,
        restricted=False,
    )
    service_two = service_json(
        id_=fake_uuid,
        name="service_two",
        users=[fake_uuid],
        message_limit=1000,
        active=True,
        restricted=True,
    )
    service_one['statistics'] = {
        'email': {'requested': 0, 'delivered': 0, 'failed': 0},
        'sms': {'requested': 0, 'delivered': 0, 'failed': 0}
    }
    service_two['statistics'] = {
        'email': {'requested': 0, 'delivered': 0, 'failed': 0},
        'sms': {'requested': 0, 'delivered': 0, 'failed': 0}
    }
    services = {'data': [service_one, service_two]}

    return mocker.patch('app.service_api_client.get_services', return_value=services)


@pytest.fixture(scope='function')
def mock_service_name_is_not_unique(mocker):
    return mocker.patch('app.service_api_client.is_service_name_unique', return_value=False)


@pytest.fixture(scope='function')
def mock_service_name_is_unique(mocker):
    return mocker.patch('app.service_api_client.is_service_name_unique', return_value=True)


@pytest.fixture(scope='function')
def mock_get_live_service(mocker, api_user_active):
    def _get(service_id):
        service = service_json(
            service_id,
            users=[api_user_active.id],
            restricted=False)
        return {'data': service}

    return mocker.patch('app.service_api_client.get_service', side_effect=_get)


@pytest.fixture(scope='function')
def mock_create_service(mocker):
    def _create(service_name, message_limit, restricted, user_id, email_from):
        service = service_json(
            101, service_name, [user_id], message_limit=message_limit, restricted=restricted, email_from=email_from)
        return service['id']

    return mocker.patch(
        'app.service_api_client.create_service', side_effect=_create)


@pytest.fixture(scope='function')
def mock_create_duplicate_service(mocker):
    def _create(service_name, message_limit, restricted, user_id, email_from):
        json_mock = Mock(return_value={'message': {'name': ["Duplicate service name '{}'".format(service_name)]}})
        resp_mock = Mock(status_code=400, json=json_mock)
        http_error = HTTPError(response=resp_mock, message="Default message")
        raise http_error

    return mocker.patch(
        'app.service_api_client.create_service', side_effect=_create)


@pytest.fixture(scope='function')
def mock_update_service(mocker):
    def _update(service_id, **kwargs):
        service = service_json(
            service_id,
            **{key: kwargs[key] for key in kwargs if key in [
                'name',
                'users',
                'message_limit',
                'active',
                'restricted',
                'email_from',
                'reply_to_email_address',
                'sms_sender',
                'permissions'
            ]}
        )
        return {'data': service}

    return mocker.patch(
        'app.service_api_client.update_service', side_effect=_update, autospec=True)


@pytest.fixture(scope='function')
def mock_update_service_raise_httperror_duplicate_name(mocker):
    def _update(
        service_id,
        **kwargs
    ):
        json_mock = Mock(return_value={'message': {'name': ["Duplicate service name '{}'".format(kwargs.get('name'))]}})
        resp_mock = Mock(status_code=400, json=json_mock)
        http_error = HTTPError(response=resp_mock, message="Default message")
        raise http_error

    return mocker.patch(
        'app.service_api_client.update_service', side_effect=_update)


SERVICE_ONE_ID = "596364a0-858e-42c8-9062-a8fe822260eb"
SERVICE_TWO_ID = "147ad62a-2951-4fa1-9ca0-093cd1a52c52"


@pytest.fixture(scope='function')
def mock_get_services(mocker, fake_uuid, user=None):
    if user is None:
        user = active_user_with_permissions(fake_uuid)

    def _get_services(params_dict=None):
        service_one = service_json(
            SERVICE_ONE_ID, "service_one", [user.id], 1000, True, False)
        service_two = service_json(
            SERVICE_TWO_ID, "service_two", [user.id], 1000, True, False)
        return {'data': [service_one, service_two]}

    return mocker.patch(
        'app.service_api_client.get_services', side_effect=_get_services)


@pytest.fixture(scope='function')
def mock_get_services_with_no_services(mocker, fake_uuid, user=None):
    if user is None:
        user = active_user_with_permissions(fake_uuid)

    def _get_services(params_dict=None):
        return {'data': []}

    return mocker.patch(
        'app.service_api_client.get_services', side_effect=_get_services)


@pytest.fixture(scope='function')
def mock_get_services_with_one_service(mocker, fake_uuid, user=None):
    if user is None:
        user = api_user_active(fake_uuid)

    def _get_services(params_dict=None):
        return {'data': [service_json(
            SERVICE_ONE_ID, "service_one", [user.id], 1000, True, True
        )]}

    return mocker.patch(
        'app.service_api_client.get_services', side_effect=_get_services)


@pytest.fixture(scope='function')
def mock_get_service_template(mocker):
    def _get(service_id, template_id, version=None):
        template = template_json(
            service_id, template_id, "Two week reminder", "sms", "Template <em>content</em> with & entity")
        if version:
            template.update({'version': version})
        return {'data': template}

    return mocker.patch(
        'app.service_api_client.get_service_template',
        side_effect=_get
    )


@pytest.fixture(scope='function')
def mock_get_service_template_with_priority(mocker):
    def _get(service_id, template_id, version=None):

        template = template_json(
            service_id, template_id, "Two week reminder", "sms", "Template <em>content</em> with & entity",
            process_type='priority')
        if version:
            template.update({'version': version})
        return {'data': template}

    return mocker.patch(
        'app.service_api_client.get_service_template',
        side_effect=_get
    )


@pytest.fixture(scope='function')
def mock_get_deleted_template(mocker):
    def _get(service_id, template_id, version=None):
        template = template_json(
            service_id,
            template_id,
            "Two week reminder",
            "sms",
            "Template <em>content</em> with & entity",
            archived=True
        )
        if version:
            template.update({'version': version})
        return {'data': template}

    return mocker.patch(
        'app.service_api_client.get_service_template',
        side_effect=_get
    )


@pytest.fixture(scope='function')
def mock_get_template_version(mocker, fake_uuid, user=None):
    if user is None:
        user = api_user_active(fake_uuid)

    def _get(service_id, template_id, version):
        template_version = template_version_json(
            service_id,
            template_id,
            user,
            version=version
        )
        return {'data': template_version}

    return mocker.patch(
        'app.service_api_client.get_service_template',
        side_effect=_get
    )


@pytest.fixture(scope='function')
def mock_get_template_versions(mocker, fake_uuid, user=None):
    if user is None:
        user = api_user_active(fake_uuid)

    def _get(service_id, template_id):
        template_version = template_version_json(
            service_id,
            template_id,
            user,
            version=1
        )
        return {'data': [template_version]}

    return mocker.patch(
        'app.service_api_client.get_service_template_versions',
        side_effect=_get
    )


@pytest.fixture(scope='function')
def mock_get_service_template_with_placeholders(mocker):
    def _get(service_id, template_id):
        template = template_json(
            service_id, template_id, "Two week reminder", "sms", "((name)), Template <em>content</em> with & entity"
        )
        return {'data': template}

    return mocker.patch(
        'app.service_api_client.get_service_template',
        side_effect=_get
    )


@pytest.fixture(scope='function')
def mock_get_service_email_template(mocker, content=None, subject=None, redact_personalisation=False):
    def _get(service_id, template_id, version=None):
        template = template_json(
            service_id,
            template_id,
            "Two week reminder",
            "email",
            content or "Your vehicle tax expires on ((date))",
            subject or "Your ((thing)) is due soon",
            redact_personalisation=redact_personalisation,
        )
        return {'data': template}

    return mocker.patch(
        'app.service_api_client.get_service_template', side_effect=_get)


@pytest.fixture(scope='function')
def mock_get_service_email_template_without_placeholders(mocker):
    return mock_get_service_email_template(
        mocker,
        content="Your vehicle tax expires soon",
        subject="Your thing is due soon",
    )


@pytest.fixture(scope='function')
def mock_get_service_letter_template(mocker, content=None, subject=None):
    def _get(service_id, template_id, version=None):
        template = template_json(
            service_id,
            template_id,
            "Two week reminder",
            "letter",
            content or "Template <em>content</em> with & entity",
            subject or "Subject",
        )
        return {'data': template}

    return mocker.patch(
        'app.service_api_client.get_service_template', side_effect=_get
    )


@pytest.fixture(scope='function')
def mock_create_service_template(mocker, fake_uuid):
    def _create(name, type_, content, service, subject=None, process_type=None):
        template = template_json(fake_uuid, name, type_, content, service, process_type)
        return {'data': template}

    return mocker.patch(
        'app.service_api_client.create_service_template',
        side_effect=_create)


@pytest.fixture(scope='function')
def mock_update_service_template(mocker):
    def _update(id_, name, type_, content, service, subject=None, process_type=None):
        template = template_json(service, id_, name, type_, content, subject, process_type)
        return {'data': template}

    return mocker.patch(
        'app.service_api_client.update_service_template',
        side_effect=_update)


@pytest.fixture(scope='function')
def mock_create_service_template_content_too_big(mocker):
    def _create(name, type_, content, service, subject=None, process_type=None):
        json_mock = Mock(return_value={
            'message': {'content': ["Content has a character count greater than the limit of 459"]},
            'result': 'error'
        })
        resp_mock = Mock(status_code=400, json=json_mock)
        http_error = HTTPError(
            response=resp_mock,
            message={'content': ["Content has a character count greater than the limit of 459"]})
        raise http_error

    return mocker.patch(
        'app.service_api_client.create_service_template',
        side_effect=_create)


@pytest.fixture(scope='function')
def mock_update_service_template_400_content_too_big(mocker):
    def _update(id_, name, type_, content, service, subject=None, process_type=None):
        json_mock = Mock(return_value={
            'message': {'content': ["Content has a character count greater than the limit of 459"]},
            'result': 'error'
        })
        resp_mock = Mock(status_code=400, json=json_mock)
        http_error = HTTPError(
            response=resp_mock,
            message={'content': ["Content has a character count greater than the limit of 459"]})
        raise http_error

    return mocker.patch(
        'app.service_api_client.update_service_template',
        side_effect=_update)


@pytest.fixture(scope='function')
def mock_get_service_templates(mocker):
    uuid1 = str(generate_uuid())
    uuid2 = str(generate_uuid())
    uuid3 = str(generate_uuid())
    uuid4 = str(generate_uuid())

    def _create(service_id):
        return {'data': [
            template_json(
                service_id, uuid1, "sms_template_one", "sms", "sms template one content"
            ),
            template_json(
                service_id, uuid2, "sms_template_two", "sms", "sms template two content"
            ),
            template_json(
                service_id, uuid3, "email_template_one", "email", "email template one content",
                subject='email template one subject',
            ),
            template_json(
                service_id, uuid4, "email_template_two", "email", "email template two content",
                subject='email template two subject',
            )
        ]}

    return mocker.patch(
        'app.service_api_client.get_service_templates',
        side_effect=_create)


@pytest.fixture(scope='function')
def mock_get_service_templates_when_no_templates_exist(mocker):

    def _create(service_id):
        return {'data': []}

    return mocker.patch(
        'app.service_api_client.get_service_templates',
        side_effect=_create)


@pytest.fixture(scope='function')
def mock_get_service_templates_with_only_one_template(mocker):

    def _get(service_id):
        return {'data': [
            template_json(
                service_id, generate_uuid(), "sms_template_one", "sms", "sms template one content"
            )
        ]}

    return mocker.patch(
        'app.service_api_client.get_service_templates',
        side_effect=_get)


@pytest.fixture(scope='function')
def mock_delete_service_template(mocker):
    def _delete(service_id, template_id):
        template = template_json(
            service_id, template_id, "Template to delete", "sms", "content to be deleted")
        return {'data': template}

    return mocker.patch(
        'app.service_api_client.delete_service_template', side_effect=_delete)


@pytest.fixture(scope='function')
def mock_redact_template(mocker):
    return mocker.patch('app.service_api_client.redact_service_template')


@pytest.fixture(scope='function')
def api_user_pending(fake_uuid):
    from app.notify_client.user_api_client import User
    user_data = {'id': fake_uuid,
                 'name': 'Test User',
                 'password': 'somepassword',
                 'email_address': 'test@user.gov.uk',
                 'mobile_number': '07700 900762',
                 'state': 'pending',
                 'failed_login_count': 0,
                 'permissions': {}
                 }
    user = User(user_data)
    return user


@pytest.fixture(scope='function')
def platform_admin_user(fake_uuid):
    from app.notify_client.user_api_client import User
    user_data = {'id': fake_uuid,
                 'name': 'Platform admin user',
                 'password': 'somepassword',
                 'email_address': 'platform@admin.gov.uk',
                 'mobile_number': '07700 900762',
                 'state': 'active',
                 'failed_login_count': 0,
                 'permissions': {SERVICE_ONE_ID: ['send_texts',
                                                  'send_emails',
                                                  'send_letters',
                                                  'manage_users',
                                                  'manage_templates',
                                                  'manage_settings',
                                                  'manage_api_keys',
                                                  'view_activity']},
                 'platform_admin': True
                 }
    user = User(user_data)
    return user


@pytest.fixture(scope='function')
def api_user_active(fake_uuid, email_address='test@user.gov.uk'):
    from app.notify_client.user_api_client import User
    user_data = {'id': fake_uuid,
                 'name': 'Test User',
                 'password': 'somepassword',
                 'email_address': email_address,
                 'mobile_number': '07700 900762',
                 'state': 'active',
                 'failed_login_count': 0,
                 'permissions': {},
                 'platform_admin': False,
                 'password_changed_at': str(datetime.utcnow())
                 }
    user = User(user_data)
    return user


@pytest.fixture(scope='function')
def api_nongov_user_active(fake_uuid):
    from app.notify_client.user_api_client import User
    user_data = {'id': fake_uuid,
                 'name': 'Test User',
                 'password': 'somepassword',
                 'email_address': 'someuser@notonwhitelist.com',
                 'mobile_number': '07700 900762',
                 'state': 'active',
                 'failed_login_count': 0,
                 'permissions': {},
                 'platform_admin': False,
                 'password_changed_at': str(datetime.utcnow())
                 }
    user = User(user_data)
    return user


@pytest.fixture(scope='function')
def active_user_with_permissions(fake_uuid):
    from app.notify_client.user_api_client import User

    user_data = {'id': fake_uuid,
                 'name': 'Test User',
                 'password': 'somepassword',
                 'password_changed_at': str(datetime.utcnow()),
                 'email_address': 'test@user.gov.uk',
                 'mobile_number': '07700 900762',
                 'state': 'active',
                 'failed_login_count': 0,
                 'permissions': {SERVICE_ONE_ID: ['send_texts',
                                                  'send_emails',
                                                  'send_letters',
                                                  'manage_users',
                                                  'manage_templates',
                                                  'manage_settings',
                                                  'manage_api_keys',
                                                  'view_activity']},
                 'platform_admin': False
                 }
    user = User(user_data)
    return user


@pytest.fixture
def active_user_view_permissions(fake_uuid):
    from app.notify_client.user_api_client import User

    user_data = {'id': fake_uuid,
                 'name': 'Test User With Permissions',
                 'password': 'somepassword',
                 'password_changed_at': str(datetime.utcnow()),
                 'email_address': 'test@user.gov.uk',
                 'mobile_number': '07700 900762',
                 'state': 'active',
                 'failed_login_count': 0,
                 'permissions': {SERVICE_ONE_ID: ['view_activity']},
                 'platform_admin': False
                 }
    user = User(user_data)
    return user


@pytest.fixture(scope='function')
def api_user_locked(fake_uuid):
    from app.notify_client.user_api_client import User
    user_data = {'id': fake_uuid,
                 'name': 'Test User',
                 'password': 'somepassword',
                 'email_address': 'test@user.gov.uk',
                 'mobile_number': '07700 900762',
                 'state': 'active',
                 'failed_login_count': 5,
                 'permissions': {}
                 }
    user = User(user_data)
    return user


@pytest.fixture(scope='function')
def api_user_request_password_reset(fake_uuid):
    from app.notify_client.user_api_client import User
    user_data = {'id': fake_uuid,
                 'name': 'Test User',
                 'password': 'somepassword',
                 'email_address': 'test@user.gov.uk',
                 'mobile_number': '07700 900762',
                 'state': 'active',
                 'failed_login_count': 5,
                 'permissions': {},
                 'password_changed_at': None
                 }
    user = User(user_data)
    return user


@pytest.fixture(scope='function')
def api_user_changed_password(fake_uuid):
    from app.notify_client.user_api_client import User
    user_data = {'id': fake_uuid,
                 'name': 'Test User',
                 'password': 'somepassword',
                 'email_address': 'test@user.gov.uk',
                 'mobile_number': '07700 900762',
                 'state': 'active',
                 'failed_login_count': 5,
                 'permissions': {},
                 'password_changed_at': str(datetime.utcnow() + timedelta(minutes=1))
                 }
    user = User(user_data)
    return user


@pytest.fixture(scope='function')
def mock_send_change_email_verification(mocker):
    return mocker.patch('app.user_api_client.send_change_email_verification')


@pytest.fixture(scope='function')
def mock_register_user(mocker, api_user_pending):
    def _register(name, email_address, mobile_number, password):
        api_user_pending.name = name
        api_user_pending.email_address = email_address
        api_user_pending.mobile_number = mobile_number
        api_user_pending.password = password
        return api_user_pending

    return mocker.patch('app.user_api_client.register_user', side_effect=_register)


@pytest.fixture(scope='function')
def mock_get_non_govuser(mocker, user=None):
    if user is None:
        user = api_user_active(fake_uuid(), email_address='someuser@notonwhitelist.com')

    def _get_user(id_):
        user.id = id_
        return user

    return mocker.patch(
        'app.user_api_client.get_user', side_effect=_get_user)


@pytest.fixture(scope='function')
def mock_get_user(mocker, user=None):
    if user is None:
        user = api_user_active(fake_uuid())

    def _get_user(id_):
        user.id = id_
        return user

    return mocker.patch(
        'app.user_api_client.get_user', side_effect=_get_user)


@pytest.fixture(scope='function')
def mock_get_locked_user(mocker, api_user_locked):
    return mock_get_user(mocker, user=api_user_locked)


@pytest.fixture(scope='function')
def mock_get_user_locked(mocker, api_user_locked):
    return mocker.patch(
        'app.user_api_client.get_user', return_value=api_user_locked)


@pytest.fixture(scope='function')
def mock_get_user_pending(mocker, api_user_pending):
    return mocker.patch(
        'app.user_api_client.get_user', return_value=api_user_pending)


@pytest.fixture(scope='function')
def mock_get_user_by_email(mocker, user=None):
    if user is None:
        user = api_user_active(fake_uuid())

    def _get_user(email_address):
        user._email_address = email_address
        return user

    return mocker.patch('app.user_api_client.get_user_by_email', side_effect=_get_user)


@pytest.fixture(scope='function')
def mock_get_locked_user_by_email(mocker, api_user_locked):
    return mock_get_user_by_email(mocker, user=api_user_locked)


@pytest.fixture(scope='function')
def mock_get_user_with_permissions(mocker, api_user_active):
    def _get_user(id):
        api_user_active._permissions[''] = ['manage_users', 'manage_templates', 'manage_settings']
        return api_user_active

    return mocker.patch(
        'app.user_api_client.get_user', side_effect=_get_user)


@pytest.fixture(scope='function')
def mock_dont_get_user_by_email(mocker):
    def _get_user(email_address):
        return None

    return mocker.patch(
        'app.user_api_client.get_user_by_email',
        side_effect=_get_user,
        autospec=True
    )


@pytest.fixture(scope='function')
def mock_get_user_by_email_request_password_reset(mocker, api_user_request_password_reset):
    return mocker.patch(
        'app.user_api_client.get_user_by_email',
        return_value=api_user_request_password_reset)


@pytest.fixture(scope='function')
def mock_get_user_by_email_user_changed_password(mocker, api_user_changed_password):
    return mocker.patch(
        'app.user_api_client.get_user_by_email',
        return_value=api_user_changed_password)


@pytest.fixture(scope='function')
def mock_get_user_by_email_locked(mocker, api_user_locked):
    return mocker.patch(
        'app.user_api_client.get_user_by_email', return_value=api_user_locked)


@pytest.fixture(scope='function')
def mock_get_user_by_email_inactive(mocker, api_user_pending):
    return mocker.patch('app.user_api_client.get_user_by_email', return_value=api_user_pending)


@pytest.fixture(scope='function')
def mock_get_user_by_email_pending(mocker, api_user_pending):
    return mocker.patch(
        'app.user_api_client.get_user_by_email',
        return_value=api_user_pending)


@pytest.fixture(scope='function')
def mock_get_user_by_email_not_found(mocker, api_user_active):
    def _get_user(email):
        json_mock = Mock(return_value={'message': "Not found", 'result': 'error'})
        resp_mock = Mock(status_code=404, json=json_mock)
        http_error = HTTPError(response=resp_mock, message="Default message")
        raise http_error

    return mocker.patch(
        'app.user_api_client.get_user_by_email',
        side_effect=_get_user)


@pytest.fixture(scope='function')
def mock_verify_password(mocker):
    def _verify_password(user, password):
        return True

    return mocker.patch(
        'app.user_api_client.verify_password',
        side_effect=_verify_password)


@pytest.fixture(scope='function')
def mock_update_user(mocker, api_user_active):
    def _update(user_id, **kwargs):
        return api_user_active

    return mocker.patch('app.user_api_client.update_user', side_effect=_update)


@pytest.fixture(scope='function')
def mock_update_user_password(mocker, api_user_active):
    def _update(user_id, **kwargs):
        return api_user_active

    return mocker.patch('app.user_api_client.update_password', side_effect=_update)


@pytest.fixture(scope='function')
def mock_update_user_attribute(mocker, api_user_active):
    def _update(user_id, **kwargs):
        return api_user_active

    return mocker.patch('app.user_api_client.update_user_attribute', side_effect=_update)


@pytest.fixture(scope='function')
def mock_is_email_unique(mocker):
    return mocker.patch('app.user_api_client.is_email_unique', return_value=True)


@pytest.fixture(scope='function')
def mock_is_email_not_unique(mocker):
    return mocker.patch('app.user_api_client.is_email_unique', return_value=False)


@pytest.fixture(scope='function')
def mock_get_all_users_from_api(mocker):
    return mocker.patch('app.user_api_client.get_users', return_value={'data': []})


@pytest.fixture(scope='function')
def mock_create_api_key(mocker):
    def _create(service_id, key_name):
        return str(generate_uuid())

    return mocker.patch('app.api_key_api_client.create_api_key', side_effect=_create)


@pytest.fixture(scope='function')
def mock_revoke_api_key(mocker):
    def _revoke(service_id, key_id):
        return {}

    return mocker.patch(
        'app.api_key_api_client.revoke_api_key',
        side_effect=_revoke)


@pytest.fixture(scope='function')
def mock_get_api_keys(mocker):
    def _get_keys(service_id, key_id=None):
        keys = {'apiKeys': [api_key_json(service_id, 'some key name'),
                            api_key_json(service_id, 'another key name', expiry_date=str(date.fromtimestamp(0)))]}
        return keys

    return mocker.patch('app.api_key_api_client.get_api_keys', side_effect=_get_keys)


@pytest.fixture(scope='function')
def mock_get_no_api_keys(mocker):
    def _get_keys(service_id):
        keys = {'apiKeys': []}
        return keys

    return mocker.patch('app.api_key_api_client.get_api_keys', side_effect=_get_keys)


@pytest.fixture(scope='function')
def mock_login(mocker, mock_get_user, mock_update_user, mock_events):
    def _verify_code(user_id, code, code_type):
        return True, ''

    def _no_services(params_dict=None):
        return {'data': []}

    return (
        mocker.patch(
            'app.user_api_client.check_verify_code',
            side_effect=_verify_code
        ),
        mocker.patch(
            'app.service_api_client.get_services',
            side_effect=_no_services
        )
    )


@pytest.fixture(scope='function')
def mock_send_verify_code(mocker):
    return mocker.patch('app.user_api_client.send_verify_code')


@pytest.fixture(scope='function')
def mock_send_verify_email(mocker):
    return mocker.patch('app.user_api_client.send_verify_email')


@pytest.fixture(scope='function')
def mock_check_verify_code(mocker):
    def _verify(user_id, code, code_type):
        return True, ''

    return mocker.patch(
        'app.user_api_client.check_verify_code',
        side_effect=_verify)


@pytest.fixture(scope='function')
def mock_check_verify_code_code_not_found(mocker):
    def _verify(user_id, code, code_type):
        return False, 'Code not found'

    return mocker.patch(
        'app.user_api_client.check_verify_code',
        side_effect=_verify)


@pytest.fixture(scope='function')
def mock_check_verify_code_code_expired(mocker):
    def _verify(user_id, code, code_type):
        return False, 'Code has expired'

    return mocker.patch(
        'app.user_api_client.check_verify_code',
        side_effect=_verify)


@pytest.fixture(scope='function')
def mock_create_job(mocker, api_user_active):
    def _create(job_id, service_id, template_id, file_name, notification_count, scheduled_for=None):
        return job_json(
            service_id,
            api_user_active,
            job_id=job_id,
            template_id=template_id,
            bucket_name='service-{}-notify'.format(job_id),
            original_file_name='{}.csv'.format(job_id),
            notification_count=notification_count)

    return mocker.patch('app.job_api_client.create_job', side_effect=_create)


@pytest.fixture(scope='function')
def mock_get_job(mocker, api_user_active):
    def _get_job(service_id, job_id):
        return {"data": job_json(service_id, api_user_active, job_id=job_id)}

    return mocker.patch('app.job_api_client.get_job', side_effect=_get_job)


@pytest.fixture(scope='function')
def mock_get_scheduled_job(mocker, api_user_active):
    def _get_job(service_id, job_id):
        return {"data": job_json(
            service_id,
            api_user_active,
            job_id=job_id,
            job_status='scheduled',
            scheduled_for='2016-01-02T00:00:00.061258'
        )}

    return mocker.patch('app.job_api_client.get_job', side_effect=_get_job)


@pytest.fixture(scope='function')
def mock_get_cancelled_job(mocker, api_user_active):
    def _get_job(service_id, job_id):
        return {"data": job_json(
            service_id,
            api_user_active,
            job_id=job_id,
            job_status='cancelled',
            scheduled_for='2016-01-01T00:00:00.061258'
        )}

    return mocker.patch('app.job_api_client.get_job', side_effect=_get_job)


@pytest.fixture(scope='function')
def mock_get_job_in_progress(mocker, api_user_active):
    def _get_job(service_id, job_id):
        return {"data": job_json(
            service_id, api_user_active, job_id=job_id,
            notification_count=10,
            notifications_requested=5
        )}

    return mocker.patch('app.job_api_client.get_job', side_effect=_get_job)


@pytest.fixture(scope='function')
def mock_get_jobs(mocker, api_user_active):
    def _get_jobs(service_id, limit_days=None, statuses=None, page=1):
        if statuses is None:
            statuses = ['', 'scheduled', 'pending', 'cancelled']

        jobs = [
            job_json(
                service_id,
                api_user_active,
                original_file_name=filename,
                scheduled_for=scheduled_for,
                job_status=job_status
            )
            for filename, scheduled_for, job_status in (
                ('export 1/1/2016.xls', '', 'finished'),
                ('all email addresses.xlsx', '', 'pending'),
                ('applicants.ods', '', 'finished'),
                ('thisisatest.csv', '', 'finished'),
                ('send_me_later.csv', '2016-01-01 11:09:00.061258', 'scheduled'),
                ('even_later.csv', '2016-01-01 23:09:00.061258', 'scheduled'),
                ('full_of_regret.csv', '2016-01-01 23:09:00.061258', 'cancelled')
            )
        ]
        return {
            'data': [job for job in jobs if job['job_status'] in statuses],
            'links': {
                'prev': 'services/{}/jobs?page={}'.format(service_id, page - 1),
                'next': 'services/{}/jobs?page={}'.format(service_id, page + 1)
            }
        }

    return mocker.patch('app.job_api_client.get_jobs', side_effect=_get_jobs)


@pytest.fixture(scope='function')
def mock_get_notifications(
    mocker,
    api_user_active,
    template_content=None,
    personalisation=None,
    redact_personalisation=False,
):
    def _get_notifications(
        service_id,
        job_id=None,
        page=1,
        page_size=50,
        template_type=None,
        status=None,
        limit_days=None,
        rows=5,
        include_jobs=None,
        include_from_test_key=None,
        to=None,
    ):
        job = None
        if job_id is not None:
            job = job_json(service_id, api_user_active, job_id=job_id)
        if template_type:
            template = template_json(
                service_id,
                id_=str(generate_uuid()),
                type_=template_type[0],
                content=template_content,
                redact_personalisation=redact_personalisation,
            )
        else:
            template = template_json(
                service_id,
                id_=str(generate_uuid()),
                content=template_content,
                redact_personalisation=redact_personalisation,
            )

        return notification_json(
            service_id,
            template=template,
            rows=rows,
            job=job,
            personalisation=personalisation,
        )

    return mocker.patch(
        'app.notification_api_client.get_notifications_for_service',
        side_effect=_get_notifications
    )


@pytest.fixture(scope='function')
def mock_get_notifications_with_previous_next(mocker):
    def _get_notifications(service_id,
                           job_id=None,
                           page=1,
                           template_type=None,
                           status=None,
                           limit_days=None,
                           include_jobs=None,
                           include_from_test_key=None,
                           to=None,
                           ):
        return notification_json(service_id, with_links=True)

    return mocker.patch(
        'app.notification_api_client.get_notifications_for_service',
        side_effect=_get_notifications
    )


@pytest.fixture(scope='function')
def mock_get_notifications_with_no_notifications(mocker):
    def _get_notifications(service_id,
                           job_id=None,
                           page=1,
                           template_type=None,
                           status=None,
                           limit_days=None,
                           include_jobs=None,
                           include_from_test_key=None,
                           to=None,
                           ):
        return notification_json(service_id, rows=0)

    return mocker.patch(
        'app.notification_api_client.get_notifications_for_service',
        side_effect=_get_notifications
    )


@pytest.fixture(scope='function')
def mock_get_inbound_sms(mocker):
    def _get_inbound_sms(
        service_id,
        user_number=None,
    ):
        return [{
            'user_number': '0790090000' + str(i),
            'content': 'message-{}'.format(index + 1),
            'created_at': (datetime.utcnow() - timedelta(minutes=60 * (i + 1), seconds=index)).isoformat(),
            'id': sample_uuid(),
        } for index, i in enumerate([0, 0, 0, 2, 4, 6, 8, 8])]

    return mocker.patch(
        'app.service_api_client.get_inbound_sms',
        side_effect=_get_inbound_sms,
    )


@pytest.fixture(scope='function')
def mock_get_inbound_sms_with_no_messages(mocker):
    def _get_inbound_sms(
        service_id,
    ):
        return []

    return mocker.patch(
        'app.service_api_client.get_inbound_sms',
        side_effect=_get_inbound_sms,
    )


@pytest.fixture(scope='function')
def mock_get_inbound_sms_summary(mocker):
    def _get_inbound_sms_summary(
        service_id,
    ):
        return {
            'count': 99,
            'most_recent': datetime.utcnow().isoformat()
        }

    return mocker.patch(
        'app.service_api_client.get_inbound_sms_summary',
        side_effect=_get_inbound_sms_summary,
    )


@pytest.fixture(scope='function')
def mock_get_inbound_sms_summary_with_no_messages(mocker):
    def _get_inbound_sms_summary(
        service_id,
    ):
        return {
            'count': 0,
            'latest_message': None
        }

    return mocker.patch(
        'app.service_api_client.get_inbound_sms_summary',
        side_effect=_get_inbound_sms_summary,
    )


@pytest.fixture(scope='function')
def mock_has_permissions(mocker):
    def _has_permission(permissions=None, any_=False, admin_override=False):
        return True

    return mocker.patch(
        'app.notify_client.user_api_client.User.has_permissions',
        side_effect=_has_permission)


@pytest.fixture(scope='function')
def mock_get_users_by_service(mocker):
    def _get_users_for_service(service_id):
        data = [{'id': 1,
                 'logged_in_at': None,
                 'mobile_number': '+447700900986',
                 'permissions': {SERVICE_ONE_ID: ['send_texts',
                                                  'send_emails',
                                                  'send_letters',
                                                  'manage_users',
                                                  'manage_templates',
                                                  'manage_settings',
                                                  'manage_api_keys',
                                                  'access_developer_docs']},
                 'state': 'active',
                 'password_changed_at': None,
                 'name': 'Test User',
                 'email_address': 'notify@digital.cabinet-office.gov.uk',
                 'failed_login_count': 0}]
        return [User(data[0])]

    return mocker.patch('app.user_api_client.get_users_for_service', side_effect=_get_users_for_service, autospec=True)


@pytest.fixture(scope='function')
def mock_s3_upload(mocker):
    def _upload(service_id, filedata, region):
        return fake_uuid()

    return mocker.patch('app.main.views.send.s3upload', side_effect=_upload)


@pytest.fixture(scope='function')
def mock_s3_download(mocker, content=None):
    if not content:
        content = """
            phone number,name
            +447700900986,John
            +447700900986,Smith
        """

    def _download(service_id, upload_id):
        return content
    return mocker.patch('app.main.views.send.s3download', side_effect=_download)


@pytest.fixture(scope='function')
def sample_invite(mocker, service_one, status='pending'):
    id_ = str(generate_uuid())
    from_user = service_one['users'][0]
    email_address = 'invited_user@test.gov.uk'
    service_id = service_one['id']
    permissions = 'send_messages,manage_service,manage_api_keys'
    created_at = str(datetime.utcnow())
    return invite_json(id_, from_user, service_id, email_address, permissions, created_at, status)


@pytest.fixture(scope='function')
def sample_invited_user(mocker, sample_invite):
    return InvitedUser(**sample_invite)


@pytest.fixture(scope='function')
def mock_create_invite(mocker, sample_invite):
    def _create_invite(from_user, service_id, email_address, permissions):
        sample_invite['from_user'] = from_user
        sample_invite['service'] = service_id
        sample_invite['email_address'] = email_address
        sample_invite['status'] = 'pending'
        sample_invite['permissions'] = permissions
        return InvitedUser(**sample_invite)

    return mocker.patch('app.invite_api_client.create_invite', side_effect=_create_invite)


@pytest.fixture(scope='function')
def mock_get_invites_for_service(mocker, service_one, sample_invite):
    import copy

    def _get_invites(service_id):
        data = []
        for i in range(0, 5):
            invite = copy.copy(sample_invite)
            invite['email_address'] = 'user_{}@testnotify.gov.uk'.format(i)
            data.append(InvitedUser(**invite))
        return data

    return mocker.patch('app.invite_api_client.get_invites_for_service', side_effect=_get_invites)


@pytest.fixture(scope='function')
def mock_check_invite_token(mocker, sample_invite):
    def _check_token(token):
        return InvitedUser(**sample_invite)

    return mocker.patch('app.invite_api_client.check_token', side_effect=_check_token)


@pytest.fixture(scope='function')
def mock_accept_invite(mocker, sample_invite):
    def _accept(service_id, invite_id):
        return InvitedUser(**sample_invite)

    return mocker.patch('app.invite_api_client.accept_invite', side_effect=_accept)


@pytest.fixture(scope='function')
def mock_add_user_to_service(mocker, service_one, api_user_active):
    def _add_user(service_id, user_id, permissions):
        return api_user_active

    return mocker.patch('app.user_api_client.add_user_to_service', side_effect=_add_user)


@pytest.fixture(scope='function')
def mock_set_user_permissions(mocker):
    return mocker.patch('app.user_api_client.set_user_permissions', return_value=None)


@pytest.fixture(scope='function')
def mock_remove_user_from_service(mocker):
    return mocker.patch('app.service_api_client.remove_user_from_service', return_value=None)


@pytest.fixture(scope='function')
def mock_get_template_statistics(mocker, service_one, fake_uuid):
    template = template_json(service_one['id'], fake_uuid, "Test template", "sms", "Something very interesting")
    data = {
        "count": 1,
        "template_name": template['name'],
        "template_type": template['template_type'],
        "template_id": template['id'],
        "day": "2016-04-04"
    }

    def _get_stats(service_id, limit_days=None):
        return [data]

    return mocker.patch(
        'app.template_statistics_client.get_template_statistics_for_service', side_effect=_get_stats)


@pytest.fixture(scope='function')
def mock_get_monthly_template_statistics(mocker, service_one, fake_uuid):
    def _stats(service_id, year):
        return {
            datetime.utcnow().strftime('%Y-%m'): {
                fake_uuid: {
                    "counts": {
                        "sending": 1,
                        "delivered": 1,
                    },
                    "name": 'My first template',
                    "type": 'sms',
                }
            }
        }
    return mocker.patch(
        'app.template_statistics_client.get_monthly_template_statistics_for_service',
        side_effect=_stats
    )


@pytest.fixture(scope='function')
def mock_get_monthly_notification_stats(mocker, service_one, fake_uuid):
    def _stats(service_id, year):
        return {'data': {
            datetime.utcnow().strftime('%Y-%m'): {
                "email": {
                    "sending": 1,
                    "delivered": 1,
                },
                "sms": {
                    "sending": 1,
                    "delivered": 1,
                },
            }
        }}
    return mocker.patch(
        'app.service_api_client.get_monthly_notification_stats',
        side_effect=_stats
    )


@pytest.fixture(scope='function')
def mock_get_template_statistics_for_template(mocker, service_one):
    def _get_stats(service_id, template_id):
        template = template_json(service_id, template_id, "Test template", "sms", "Something very interesting")
        notification = single_notification_json(service_id, template=template)
        return notification

    return mocker.patch(
        'app.template_statistics_client.get_template_statistics_for_template', side_effect=_get_stats)


@pytest.fixture(scope='function')
def mock_get_usage(mocker, service_one, fake_uuid):
    def _get_usage(service_id, year=None):
        return [
            {"international": False, "rate": 0.0165, "rate_multiplier": 1,
             "notification_type": "sms", "billing_units": 251500},
            {"international": True, "rate": 0.0165, "rate_multiplier": 1,
             "notification_type": "sms", "billing_units": 300},
            {"international": True, "rate": 0.0165, "rate_multiplier": 2,
             "notification_type": "sms", "billing_units": 150},
            {"international": True, "rate": 0.0165, "rate_multiplier": 3,
             "notification_type": "sms", "billing_units": 30},
            {"international": False, "rate": 0.0165, "notification_type": "email",
             "rate_multiplier": None, "billing_units": 1000}
        ]

    return mocker.patch(
        'app.billing_api_client.get_service_usage', side_effect=_get_usage)


@pytest.fixture(scope='function')
def mock_get_yearly_sms_unit_count_and_cost(mocker, service_one, fake_uuid):
    def _get_usage(service_id, year=None):
        return {"billable_sms_units": 100, "total_cost": 200.0}

    return mocker.patch(
        'app.service_api_client.get_yearly_sms_unit_count_and_cost', side_effect=_get_usage)


@pytest.fixture(scope='function')
def mock_get_billable_units(mocker):
    def _get_usage(service_id, year):
        return [
            {
                'month': 'April',
                'international': False,
                'rate_multiplier': 1,
                'notification_type': 'sms',
                'rate': 0.0165,
                'billing_units': 249500
            },
            {
                'month': 'April',
                'international': True,
                'rate_multiplier': 1,
                'notification_type': 'sms',
                'rate': 0.0165,
                'billing_units': 100
            },
            {
                'month': 'April',
                'international': True,
                'rate_multiplier': 2,
                'notification_type': 'sms',
                'rate': 0.0165,
                'billing_units': 100
            },
            {
                'month': 'April',
                'international': True,
                'rate_multiplier': 3,
                'notification_type': 'sms',
                'rate': 0.0165,
                'billing_units': 20
            },
            {
                'month': 'March',
                'international': False,
                'rate_multiplier': 1,
                'notification_type': 'sms',
                'rate': 0.0165,
                'billing_units': 1000
            },
            {
                'month': 'March',
                'international': True,
                'rate_multiplier': 1,
                'notification_type': 'sms',
                'rate': 0.0165,
                'billing_units': 100
            },
            {
                'month': 'March',
                'international': True,
                'rate_multiplier': 2,
                'notification_type': 'sms',
                'rate': 0.0165,
                'billing_units': 50
            },
            {
                'month': 'March',
                'international': True,
                'rate_multiplier': 3,
                'notification_type': 'sms',
                'rate': 0.0165,
                'billing_units': 10
            },
            {
                'month': 'February',
                'international': False,
                'rate_multiplier': 1,
                'notification_type': 'sms',
                'rate': 0.0165,
                'billing_units': 1000
            },
            {
                'month': 'February',
                'international': True,
                'rate_multiplier': 1,
                'notification_type': 'sms',
                'rate': 0.0165,
                'billing_units': 100
            },

        ]

    return mocker.patch(
        'app.billing_api_client.get_billable_units', side_effect=_get_usage)


@pytest.fixture(scope='function')
def mock_get_future_usage(mocker, service_one, fake_uuid):
    def _get_usage(service_id, year=None):
        return [
            {
                'notification_type': 'sms', 'international': False,
                'credits': 0, 'rate_multiplier': 1, 'rate': 0.0158, 'billing_units': 0
            },
            {
                'notification_type': 'email', 'international': False,
                'credits': 0, 'rate_multiplier': 1, 'rate': 0, 'billing_units': 0
            }
        ]

    return mocker.patch(
        'app.billing_api_client.get_service_usage', side_effect=_get_usage)


@pytest.fixture(scope='function')
def mock_get_future_billable_units(mocker):
    def _get_usage(service_id, year):
        return []

    return mocker.patch(
        'app.billing_api_client.get_billable_units', side_effect=_get_usage)


@pytest.fixture(scope='function')
def mock_events(mocker):
    def _create_event(event_type, event_data):
        return {'some': 'data'}

    return mocker.patch('app.events_api_client.create_event', side_effect=_create_event)


@pytest.fixture(scope='function')
def mock_send_already_registered_email(mocker):
    return mocker.patch('app.user_api_client.send_already_registered_email')


@pytest.fixture(scope='function')
def mock_get_organisations(mocker):
    def _get_organisations():
        return [
            {
                'logo': 'example.png',
                'name': 'Organisation name',
                'id': 'organisation-id',
                'colour': '#f00'
            }
        ]

    return mocker.patch(
        'app.organisations_client.get_organisations', side_effect=_get_organisations
    )


@pytest.fixture(scope='function')
def mock_get_letter_organisations(mocker):
    def _get_organisations():
        return {
            '001': 'HM Government',
            '500': 'Land Registry',
        }

    return mocker.patch(
        'app.organisations_client.get_letter_organisations', side_effect=_get_organisations
    )


@pytest.fixture(scope='function')
def mock_get_organisation(mocker):
    def _get_organisation(id):
        return {
            'organisation': {
                'logo': 'example.png',
                'name': 'Organisation name',
                'id': 'organisation-id',
                'colour': '#f00'
            }
        }

    return mocker.patch(
        'app.organisations_client.get_organisation', side_effect=_get_organisation
    )


@pytest.fixture(scope='function')
def mock_get_whitelist(mocker):
    def _get_whitelist(service_id):
        return {
            'email_addresses': ['test@example.com'],
            'phone_numbers': ['07900900000']
        }

    return mocker.patch(
        'app.service_api_client.get_whitelist', side_effect=_get_whitelist
    )


@pytest.fixture(scope='function')
def mock_update_whitelist(mocker):
    return mocker.patch(
        'app.service_api_client.update_whitelist'
    )


@pytest.fixture(scope='function')
def mock_reset_failed_login_count(mocker):
    return mocker.patch('app.user_api_client.reset_failed_login_count')


@pytest.fixture
def mock_get_notification(
    mocker,
    fake_uuid,
    notification_status='delivered',
    redact_personalisation=False,
    template_type=None,
):
    def _get_notification(
        service_id,
        notification_id,
    ):
        noti = notification_json(
            service_id,
            rows=1,
            status=notification_status,
            template_type=template_type,
        )['notifications'][0]

        noti['id'] = notification_id
        noti['created_by'] = {
            'id': fake_uuid,
            'name': 'Test User',
            'email_address': 'test@user.gov.uk'
        }
        noti['personalisation'] = {'name': 'Jo'}
        noti['template'] = template_json(
            service_id,
            '5407f4db-51c7-4150-8758-35412d42186a',
            content='hello ((name))',
            subject='blah',
            redact_personalisation=redact_personalisation,
            type_=template_type,
        )
        return noti

    return mocker.patch(
        'app.notification_api_client.get_notification',
        side_effect=_get_notification
    )


@pytest.fixture
def mock_send_notification(mocker, fake_uuid):
    def _send_notification(
        service_id, *, template_id, recipient, personalisation
    ):
        return {'id': fake_uuid}

    return mocker.patch(
        'app.notification_api_client.send_notification',
        side_effect=_send_notification
    )


@pytest.fixture(scope='function')
def client(app_):
    with app_.test_request_context(), app_.test_client() as client:
        yield client


@pytest.fixture(scope='function')
def logged_in_client(
    client,
    active_user_with_permissions,
    mocker,
    service_one,
    mock_login
):
    client.login(active_user_with_permissions, mocker, service_one)
    yield client


@pytest.fixture(scope='function')
def logged_in_platform_admin_client(
    client,
    platform_admin_user,
    mocker,
    service_one,
    mock_login,
):
    mock_get_user(mocker, user=platform_admin_user)
    client.login(platform_admin_user, mocker, service_one)
    yield client


@pytest.fixture
def os_environ():
    """
    clear os.environ, and restore it after the test runs
    """
    # for use whenever you expect code to edit environment variables
    old_env = os.environ.copy()
    os.environ = {}
    yield
    os.environ = old_env


@pytest.fixture
def client_request(logged_in_client):
    class ClientRequest:

        @staticmethod
        @contextmanager
        def session_transaction():
            with logged_in_client.session_transaction() as session:
                yield session

        @staticmethod
        def get(
            endpoint,
            _expected_status=200,
            _follow_redirects=False,
            _test_page_title=True,
            **endpoint_kwargs
        ):
            resp = logged_in_client.get(
                url_for(endpoint, **(endpoint_kwargs or {})),
                follow_redirects=_follow_redirects,
            )
            assert resp.status_code == _expected_status
            page = BeautifulSoup(resp.data.decode('utf-8'), 'html.parser')
            if _test_page_title:
                page_title, h1 = (
                    normalize_spaces(page.find(selector).text) for selector in ('title', 'h1')
                )
                if not normalize_spaces(page_title).startswith(h1):
                    raise AssertionError('Page title ‘{}’ does not start with H1 ‘{}’'.format(page_title, h1))
            return page

        @staticmethod
        def post(endpoint, _data=None, _expected_status=None, _follow_redirects=False, **endpoint_kwargs):
            if _expected_status is None:
                _expected_status = 200 if _follow_redirects else 302
            resp = logged_in_client.post(
                url_for(endpoint, **(endpoint_kwargs or {})),
                data=_data,
                follow_redirects=_follow_redirects,
            )
            assert resp.status_code == _expected_status
            return BeautifulSoup(resp.data.decode('utf-8'), 'html.parser')

    return ClientRequest


def normalize_spaces(input):
    if isinstance(input, str):
        return ' '.join(input.split())
    return normalize_spaces(' '.join(item.text for item in input))
