import pytest

from app.notify_client.service_api_client import ServiceAPIClient
from tests.conftest import fake_uuid


def test_client_posts_archived_true_when_deleting_template(mocker):
    service_id = fake_uuid
    template_id = fake_uuid
    mocker.patch('app.notify_client.current_user', id='1')

    expected_data = {
        'archived': True,
        'created_by': '1'
    }
    expected_url = '/service/{}/template/{}'.format(service_id, template_id)

    client = ServiceAPIClient()
    mock_post = mocker.patch('app.notify_client.service_api_client.ServiceAPIClient.post')

    client.delete_service_template(service_id, template_id)
    mock_post.assert_called_once_with(expected_url, data=expected_data)


@pytest.mark.parametrize(
    'function,params', [
        (ServiceAPIClient.get_service, {}),
        (ServiceAPIClient.get_detailed_service, {'detailed': True}),
        (ServiceAPIClient.get_detailed_service_for_today, {'detailed': True, 'today_only': True})
    ],
    ids=lambda x: x.__name__
)
def test_client_gets_service(mocker, function, params):
    client = ServiceAPIClient()
    mock_get = mocker.patch.object(client, 'get')

    function(client, 'foo')
    mock_get.assert_called_once_with('/service/foo', params=params)


def test_client_only_updates_allowed_attributes(mocker):
    mocker.patch('app.notify_client.current_user', id='1')
    with pytest.raises(TypeError) as error:
        ServiceAPIClient().update_service('service_id', foo='bar')
    assert str(error.value) == 'Not allowed to update service attributes: foo'
