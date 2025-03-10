import gdk.commands.component.list as list
import gdk.common.consts as consts
import gdk.common.exceptions.error_messages as error_messages
import pytest
from urllib3.exceptions import HTTPError


def test_display_list():
    components = [1, 2, 4]
    list.display_list(components)


def test_get_component_list_from_github_valid_json(mocker):
    res_json = {"template-name": "template-list"}
    url = "url"
    mock_response = mocker.Mock(status_code=200, json=lambda: res_json)
    mock_template_list = mocker.patch("requests.get", return_value=mock_response)

    templates_list = list.get_component_list_from_github(url)
    assert templates_list == res_json
    assert mock_template_list.call_count == 1


def test_get_component_list_from_github_invalid_json(mocker):
    res_json = {"template-name": "template-list"}
    mock_response = mocker.Mock(status_code=200, json=res_json)
    mock_template_list = mocker.patch("requests.get", return_value=mock_response)

    templates_list = list.get_component_list_from_github("url")
    assert templates_list == []
    assert mock_template_list.call_count == 1


def test_get_component_list_from_github_invalid_url(mocker):
    mock_response = mocker.Mock(status_code=404, raise_for_status=mocker.Mock(side_effect=HTTPError("some error")))
    mock_template_list = mocker.patch("requests.get", return_value=mock_response)

    with pytest.raises(Exception) as e:
        list.get_component_list_from_github("url")
    assert e.value.args[0] == error_messages.LISTING_COMPONENTS_FAILED
    assert mock_template_list.call_count == 1


def test_run_template(mocker):
    mock_get_component_list_from_github = mocker.patch(
        "gdk.commands.component.list.get_component_list_from_github", return_value=[]
    )
    mock_display_list = mocker.patch("gdk.commands.component.list.display_list", return_value=None)
    list.run({"template": True})
    mock_get_component_list_from_github.assert_any_call(consts.templates_list_url)
    assert mock_display_list.call_count == 1


def test_run_repository(mocker):
    mock_get_component_list_from_github = mocker.patch(
        "gdk.commands.component.list.get_component_list_from_github", return_value=[]
    )
    mock_display_list = mocker.patch("gdk.commands.component.list.display_list", return_value=None)
    list.run({"repository": True})
    mock_get_component_list_from_github.assert_any_call(consts.repository_list_url)
    assert mock_display_list.call_count == 1


def test_run_none(mocker):
    mock_get_component_list_from_github = mocker.patch(
        "gdk.commands.component.list.get_component_list_from_github", return_value=[]
    )
    mock_display_list = mocker.patch("gdk.commands.component.list.display_list", return_value=None)
    with pytest.raises(Exception) as e:
        list.run({})
    assert e.value.args[0] == error_messages.LIST_WITH_INVALID_ARGS
    assert mock_display_list.call_count == 0
    assert mock_get_component_list_from_github.call_count == 0
