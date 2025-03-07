from pathlib import Path
from shutil import Error
from unittest.mock import mock_open, patch

import gdk.common.utils as utils
import pytest
from gdk.common.exceptions import error_messages

json_values = {
    "component_name": "component_name",
    "component_build_config": {"build_system": "zip"},
    "component_version": "1.0.0",
    "component_author": "abc",
    "bucket": "default",
    "gg_build_directory": Path("/src/GDK-CLI-Internal/greengrass-build"),
    "gg_build_artifacts_dir": Path("/src/GDK-CLI-Internal/greengrass-build/artifacts"),
    "gg_build_recipes_dir": Path("/src/GDK-CLI-Internal/greengrass-build/recipes"),
    "gg_build_component_artifacts_dir": Path("/src/GDK-CLI-Internal/greengrass-build/artifacts/component_name/1.0.0"),
    "component_recipe_file": Path("/src/GDK-CLI-Internal/tests/gdk/static/build_command/valid_component_recipe.json"),
    "parsed_component_recipe": {
        "RecipeFormatVersion": "2020-01-25",
        "ComponentName": "com.example.HelloWorld",
        "ComponentVersion": "1.0.0",
        "ComponentDescription": "My first Greengrass component.",
        "ComponentPublisher": "Amazon",
        "ComponentConfiguration": {"DefaultConfiguration": {"Message": "world"}},
        "Manifests": [
            {
                "Platform": {"os": "linux"},
                "Lifecycle": {"Run": "python3 -u {artifacts:path}/hello_world.py '{configuration:/Message}'"},
                "Artifacts": [{"URI": "s3://DOC-EXAMPLE-BUCKET/artifacts/com.example.HelloWorld/1.0.0/hello_world.py"}],
            }
        ],
    },
}


def test_create_recipe_file_json_valid(mocker):
    # Tests if a new recipe file is created with updated values - json
    mock_get_parsed_config = mocker.patch(
        "gdk.commands.component.project_utils.get_project_config_values", return_value=json_values
    )

    import gdk.commands.component.build as build

    assert mock_get_parsed_config.call_count == 1
    file_name = Path(json_values["gg_build_recipes_dir"]).joinpath(json_values["component_recipe_file"].name).resolve()
    mock_json_dump = mocker.patch("json.dumps")
    mock_yaml_dump = mocker.patch("yaml.dump")
    with patch("builtins.open", mock_open()) as mock_file:
        build.create_build_recipe_file()
        mock_file.assert_any_call(file_name, "w")
        mock_json_dump.call_count == 1
        assert not mock_yaml_dump.called


def test_create_recipe_file_yaml_valid(mocker):
    # Tests if a new recipe file is created with updated values - yaml
    # Tests if a new recipe file is created with updated values - json
    import gdk.commands.component.build as build

    build.project_config["component_recipe_file"] = Path("some-yaml.yaml").resolve()
    file_name = (
        Path(json_values["gg_build_recipes_dir"])
        .joinpath(build.project_config["component_recipe_file"].resolve().name)
        .resolve()
    )
    mock_json_dump = mocker.patch("json.dumps")
    mock_yaml_dump = mocker.patch("yaml.dump")
    with patch("builtins.open", mock_open()) as mock_file:
        build.create_build_recipe_file()
        mock_file.assert_called_once_with(file_name, "w")
        mock_json_dump.call_count == 1
        assert mock_yaml_dump.called


def test_create_recipe_file_json_invalid(mocker):
    # Raise exception for when creating recipe failed due to invalid json
    import gdk.commands.component.build as build

    build.project_config["component_recipe_file"] = Path("some-json.json").resolve()
    file_name = Path(json_values["gg_build_recipes_dir"]).joinpath(json_values["component_recipe_file"].name).resolve()

    def throw_error(*args, **kwargs):
        if args[0] == json_values["parsed_component_recipe"]:
            raise TypeError("I mock json error")

    mock_json_dump = mocker.patch("json.dumps", side_effect=throw_error)
    mock_yaml_dump = mocker.patch("yaml.dump")
    with patch("builtins.open", mock_open()) as mock_file:
        with pytest.raises(Exception) as e:
            build.create_build_recipe_file()
        assert "Failed to create build recipe file at" in e.value.args[0]
        mock_file.assert_called_once_with(file_name, "w")
        mock_json_dump.call_count == 1
        assert not mock_yaml_dump.called


def test_create_recipe_file_yaml_invalid(mocker):
    # Raise exception for when creating recipe failed due to invalid yaml
    import gdk.commands.component.build as build

    build.project_config["component_recipe_file"] = Path("some-yaml.yaml").resolve()
    file_name = (
        Path(json_values["gg_build_recipes_dir"]).joinpath(build.project_config["component_recipe_file"].name).resolve()
    )

    def throw_error(*args, **kwargs):
        if args[0] == json_values["parsed_component_recipe"]:
            raise TypeError("I mock yaml error")

    mock_json_dump = mocker.patch("json.dumps")
    mock_yaml_dump = mocker.patch("yaml.dump", side_effect=throw_error)
    with patch("builtins.open", mock_open()) as mock_file:
        with pytest.raises(Exception) as e:
            build.create_build_recipe_file()
        assert "Failed to create build recipe file at" in e.value.args[0]
        mock_file.assert_called_once_with(file_name, "w")
        mock_json_dump.call_count == 1
        assert mock_yaml_dump.called


def test_get_build_folder_by_build_system():
    import gdk.commands.component.build as build

    paths = build._get_build_folder_by_build_system()
    assert len(paths) == 1
    assert Path(utils.current_directory).joinpath(*["zip-build"]).resolve() in paths


def test_create_gg_build_directories(mocker):
    mocker.patch("gdk.commands.component.project_utils.get_project_config_values", return_value=json_values)
    import gdk.commands.component.build as build

    mock_mkdir = mocker.patch("pathlib.Path.mkdir")
    mock_clean = mocker.patch("gdk.common.utils.clean_dir")
    build.create_gg_build_directories()

    assert mock_mkdir.call_count == 2
    assert mock_clean.call_count == 1

    mock_mkdir.assert_any_call(json_values["gg_build_recipes_dir"], parents=True, exist_ok=True)
    mock_mkdir.assert_any_call(json_values["gg_build_component_artifacts_dir"], parents=True, exist_ok=True)
    mock_clean.assert_called_once_with(json_values["gg_build_directory"])


def test_run_build_command_with_error_not_zip(mocker):
    mock_build_system_zip = mocker.patch("gdk.commands.component.build._build_system_zip", return_value=None)
    mock_subprocess_run = mocker.patch("subprocess.run", return_value=None, side_effect=Error("some error"))
    import gdk.commands.component.build as build

    build.project_config["component_build_config"]["build_system"] = "maven"
    with pytest.raises(Exception) as e:
        build.run_build_command()
    assert not mock_build_system_zip.called
    assert mock_subprocess_run.called
    assert "Error building the component with the given build system." in e.value.args[0]


def test_run_build_command_with_error_with_zip_build(mocker):
    mock_build_system_zip = mocker.patch(
        "gdk.commands.component.build._build_system_zip", return_value=None, side_effect=Error("some error")
    )
    import gdk.commands.component.build as build

    build.project_config["component_build_config"]["build_system"] = "zip"
    with pytest.raises(Exception) as e:
        build.run_build_command()
    assert "Error building the component with the given build system." in e.value.args[0]
    assert mock_build_system_zip.called


def test_run_build_command_not_zip_build(mocker):
    mock_build_system_zip = mocker.patch("gdk.commands.component.build._build_system_zip", return_value=None)
    mock_subprocess_run = mocker.patch("subprocess.run", return_value=None)
    import gdk.commands.component.build as build

    build.project_config["component_build_config"]["build_system"] = "maven"
    build.run_build_command()
    assert not mock_build_system_zip.called
    assert mock_subprocess_run.called


def test_run_build_command_zip_build(mocker):
    mock_build_system_zip = mocker.patch("gdk.commands.component.build._build_system_zip", return_value=None)
    mock_subprocess_run = mocker.patch("subprocess.run", return_value=None)
    import gdk.commands.component.build as build

    build.project_config["component_build_config"]["build_system"] = "zip"
    build.run_build_command()
    assert not mock_subprocess_run.called
    mock_build_system_zip.assert_called_with()


def test_build_system_zip_valid(mocker):
    # build_file = Path('mock-file.py').resolve()
    zip_build_path = Path("zip-build").resolve()
    zip_artifacts_path = Path(zip_build_path).joinpath(utils.current_directory.name).resolve()
    mock_build_info = mocker.patch(
        "gdk.commands.component.build._get_build_folder_by_build_system", return_value={zip_build_path}
    )
    mock_clean_dir = mocker.patch("gdk.common.utils.clean_dir", return_value=None)
    mock_copytree = mocker.patch("shutil.copytree")
    mock_subprocess_run = mocker.patch("subprocess.run", return_value=None)
    mock_ignore_files_during_zip = mocker.patch("gdk.commands.component.build._ignore_files_during_zip", return_value=[])
    mock_make_archive = mocker.patch("shutil.make_archive")
    import gdk.commands.component.build as build

    build.project_config["component_build_config"]["build_system"] = "zip"
    build._build_system_zip()

    assert not mock_subprocess_run.called
    mock_build_info.assert_called_with()
    mock_clean_dir.assert_called_with(zip_build_path)

    curr_dir = Path(".").resolve()

    mock_copytree.assert_called_with(curr_dir, zip_artifacts_path, ignore=mock_ignore_files_during_zip)
    assert mock_make_archive.called
    zip_build_file = Path(zip_build_path).joinpath(utils.current_directory.name).resolve()
    mock_make_archive.assert_called_with(zip_build_file, "zip", root_dir=zip_artifacts_path)


def test_ignore_files_during_zip():
    import gdk.commands.component.build as build

    path = Path(".")
    names = ["1", "2"]
    li = build._ignore_files_during_zip(path, names)
    assert type(li) == list


def test_build_system_zip_error_archive(mocker):

    zip_build_path = Path("zip-build").resolve()
    zip_artifacts_path = Path(zip_build_path).joinpath(utils.current_directory.name).resolve()

    mock_build_info = mocker.patch(
        "gdk.commands.component.build._get_build_folder_by_build_system", return_value={zip_build_path}
    )
    mock_clean_dir = mocker.patch("gdk.common.utils.clean_dir", return_value=None)
    mock_copytree = mocker.patch("shutil.copytree")
    mock_subprocess_run = mocker.patch("subprocess.run", return_value=None)
    mock_ignore_files_during_zip = mocker.patch("gdk.commands.component.build._ignore_files_during_zip", return_value=[])
    mock_make_archive = mocker.patch("shutil.make_archive", side_effect=Error("some error"))
    import gdk.commands.component.build as build

    with pytest.raises(Exception) as e:
        build._build_system_zip()

    assert "Failed to zip the component in default build mode." in e.value.args[0]
    assert not mock_subprocess_run.called
    mock_build_info.assert_called_with()
    mock_clean_dir.assert_called_with(zip_build_path)

    curr_dir = Path(".").resolve()

    mock_copytree.assert_called_with(curr_dir, zip_artifacts_path, ignore=mock_ignore_files_during_zip)
    assert mock_make_archive.called
    zip_build_file = Path(zip_build_path).joinpath(utils.current_directory.name).resolve()
    mock_make_archive.assert_called_with(zip_build_file, "zip", root_dir=zip_artifacts_path)


def test_build_system_zip_error_copytree(mocker):
    zip_build_path = Path("zip-build").resolve()
    zip_artifacts_path = Path(zip_build_path).joinpath(utils.current_directory.name).resolve()

    mock_build_info = mocker.patch(
        "gdk.commands.component.build._get_build_folder_by_build_system", return_value={zip_build_path}
    )
    mock_clean_dir = mocker.patch("gdk.common.utils.clean_dir", return_value=None)
    mock_copytree = mocker.patch("shutil.copytree", side_effect=Error("some error"))
    mock_subprocess_run = mocker.patch("subprocess.run", return_value=None)
    mock_ignore_files_during_zip = mocker.patch("gdk.commands.component.build._ignore_files_during_zip", return_value=[])
    mock_make_archive = mocker.patch("shutil.make_archive")
    import gdk.commands.component.build as build

    with pytest.raises(Exception) as e:
        build._build_system_zip()

    assert "Failed to zip the component in default build mode." in e.value.args[0]
    assert not mock_subprocess_run.called
    mock_build_info.assert_called_with()
    mock_clean_dir.assert_called_with(zip_build_path)

    curr_dir = Path(".").resolve()

    mock_copytree.assert_called_with(curr_dir, zip_artifacts_path, ignore=mock_ignore_files_during_zip)
    assert not mock_make_archive.called


def test_build_system_zip_error_get_build_folder_by_build_system(mocker):
    zip_build_path = Path("zip-build").resolve()
    mock_build_info = mocker.patch(
        "gdk.commands.component.build._get_build_folder_by_build_system",
        return_value=zip_build_path,
        side_effect=Error("some error"),
    )
    mock_clean_dir = mocker.patch("gdk.common.utils.clean_dir", return_value=None)
    mock_copytree = mocker.patch("shutil.copytree")
    mock_subprocess_run = mocker.patch("subprocess.run", return_value=None)
    mock_ignore_files_during_zip = mocker.patch("gdk.commands.component.build._ignore_files_during_zip", return_value=[])
    mock_make_archive = mocker.patch("shutil.make_archive")
    import gdk.commands.component.build as build

    with pytest.raises(Exception) as e:
        build._build_system_zip()

    assert "Failed to zip the component in default build mode." in e.value.args[0]
    assert not mock_subprocess_run.called
    mock_build_info.assert_called_with()
    assert not mock_clean_dir.called
    assert not mock_copytree.called
    assert not mock_make_archive.called
    assert not mock_ignore_files_during_zip.called


def test_build_system_zip_error_clean_dir(mocker):
    zip_build_path = Path("zip-build").resolve()
    mock_build_info = mocker.patch(
        "gdk.commands.component.build._get_build_folder_by_build_system", return_value={zip_build_path}
    )
    mock_clean_dir = mocker.patch("gdk.common.utils.clean_dir", return_value=None, side_effect=Error("some error"))
    mock_copytree = mocker.patch("shutil.copytree")
    mock_subprocess_run = mocker.patch("subprocess.run", return_value=None)
    mock_make_archive = mocker.patch("shutil.make_archive")
    import gdk.commands.component.build as build

    with pytest.raises(Exception) as e:
        build._build_system_zip()

    assert "Failed to zip the component in default build mode." in e.value.args[0]
    assert not mock_subprocess_run.called
    mock_build_info.assert_called_with()
    assert mock_clean_dir.called
    assert not mock_copytree.called
    assert not mock_make_archive.called


def test_copy_artifacts_and_update_uris_valid(mocker):
    zip_build_path = [Path("zip-build").resolve()]
    mock_build_info = mocker.patch(
        "gdk.commands.component.build._get_build_folder_by_build_system", return_value=zip_build_path
    )
    mock_shutil_copy = mocker.patch("shutil.copy")
    mock_glob = mocker.patch("pathlib.Path.glob", return_value=[Path(".").joinpath("hello_world.py")])
    import gdk.commands.component.build as build

    build.copy_artifacts_and_update_uris()
    assert mock_build_info.assert_called_once
    assert mock_glob.assert_called_once
    assert mock_shutil_copy.called


def test_copy_artifacts_and_update_uris_recipe_uri_matches(mocker):
    # Copy only if the uri in recipe matches the artifact in build folder
    zip_build_path = [Path("zip-build").resolve()]
    mock_build_info = mocker.patch(
        "gdk.commands.component.build._get_build_folder_by_build_system", return_value=zip_build_path
    )
    mock_iter_dir_list = [Path("hello_world.py").resolve()]
    mock_shutil_copy = mocker.patch("shutil.copy")
    mock_glob = mocker.patch("pathlib.Path.glob", return_value=mock_iter_dir_list)
    import gdk.commands.component.build as build

    build.copy_artifacts_and_update_uris()
    assert mock_shutil_copy.called
    assert mock_build_info.assert_called_once
    assert mock_glob.assert_called_once
    mock_shutil_copy.assert_called_with(Path("hello_world.py").resolve(), json_values["gg_build_component_artifacts_dir"])


def test_copy_artifacts_and_update_uris_recipe_uri_not_matches(mocker):
    # Do not copy if the uri in recipe doesnt match the artifact in build folder

    zip_build_path = [Path("zip-build").resolve()]
    mock_build_info = mocker.patch(
        "gdk.commands.component.build._get_build_folder_by_build_system", return_value=zip_build_path
    )
    mock_shutil_copy = mocker.patch("shutil.copy")
    mock_glob = mocker.patch("pathlib.Path.glob", return_value=[])
    import gdk.commands.component.build as build

    with pytest.raises(Exception) as e:
        build.copy_artifacts_and_update_uris()

    assert (
        "Could not find the artifact file specified in the recipe 'hello_world.py' inside the build folder" in e.value.args[0]
    )
    assert not mock_shutil_copy.called
    assert mock_build_info.assert_called_once
    assert mock_glob.assert_called_once


def test_default_build_component(mocker):
    mock_run_build_command = mocker.patch("gdk.commands.component.build.run_build_command")
    mock_copy_artifacts_and_update_uris = mocker.patch("gdk.commands.component.build.copy_artifacts_and_update_uris")
    mock_create_build_recipe_file = mocker.patch("gdk.commands.component.build.create_build_recipe_file")
    import gdk.commands.component.build as build

    build.default_build_component()
    assert mock_run_build_command.assert_called_once
    assert mock_copy_artifacts_and_update_uris.assert_called_once
    assert mock_create_build_recipe_file.assert_called_once


def test_default_build_component_error_run_build_command(mocker):
    mock_run_build_command = mocker.patch("gdk.commands.component.build.run_build_command", side_effect=Error("command"))
    mock_copy_artifacts_and_update_uris = mocker.patch("gdk.commands.component.build.copy_artifacts_and_update_uris")
    mock_create_build_recipe_file = mocker.patch("gdk.commands.component.build.create_build_recipe_file")
    import gdk.commands.component.build as build

    with pytest.raises(Exception) as e:
        build.default_build_component()

    assert "\ncommand" in e.value.args[0]
    assert error_messages.BUILD_FAILED in e.value.args[0]
    assert mock_run_build_command.assert_called_once
    assert not mock_copy_artifacts_and_update_uris.called
    assert not mock_create_build_recipe_file.called


def test_default_build_component_error_copy_artifacts_and_update_uris(mocker):
    mock_run_build_command = mocker.patch("gdk.commands.component.build.run_build_command")
    mock_copy_artifacts_and_update_uris = mocker.patch(
        "gdk.commands.component.build.copy_artifacts_and_update_uris", side_effect=Error("copying")
    )
    mock_create_build_recipe_file = mocker.patch("gdk.commands.component.build.create_build_recipe_file")
    import gdk.commands.component.build as build

    with pytest.raises(Exception) as e:
        build.default_build_component()

    assert "\ncopy" in e.value.args[0]
    assert error_messages.BUILD_FAILED in e.value.args[0]
    assert mock_run_build_command.assert_called_once
    assert mock_copy_artifacts_and_update_uris.assert_called_once
    assert not mock_create_build_recipe_file.called


def test_default_build_component_error_create_build_recipe_file(mocker):
    mock_run_build_command = mocker.patch("gdk.commands.component.build.run_build_command")
    mock_copy_artifacts_and_update_uris = mocker.patch("gdk.commands.component.build.copy_artifacts_and_update_uris")
    mock_create_build_recipe_file = mocker.patch(
        "gdk.commands.component.build.create_build_recipe_file", side_effect=Error("recipe")
    )
    import gdk.commands.component.build as build

    with pytest.raises(Exception) as e:
        build.default_build_component()

    assert "\nrecipe" in e.value.args[0]
    assert error_messages.BUILD_FAILED in e.value.args[0]
    assert mock_run_build_command.assert_called_once
    assert mock_copy_artifacts_and_update_uris.assert_called_once
    assert mock_create_build_recipe_file.assert_called_once


def test_build_run_default(mocker):
    mock_create_gg_build_directories = mocker.patch("gdk.commands.component.build.create_gg_build_directories")
    mock_default_build_component = mocker.patch("gdk.commands.component.build.default_build_component")
    mock_subprocess_run = mocker.patch("subprocess.run")
    import gdk.commands.component.build as build

    build.run({})

    assert mock_create_gg_build_directories.assert_called_once
    assert mock_default_build_component.assert_called_once
    assert not mock_subprocess_run.called


def test_build_run_custom(mocker):
    mock_create_gg_build_directories = mocker.patch("gdk.commands.component.build.create_gg_build_directories")
    mock_default_build_component = mocker.patch("gdk.commands.component.build.default_build_component")
    mock_subprocess_run = mocker.patch("subprocess.run")
    import gdk.commands.component.build as build

    modify_build = build.project_config
    modify_build["component_build_config"]["build_system"] = "custom"
    modify_build["component_build_config"]["custom_build_command"] = ["a"]
    build.run({})
    assert mock_create_gg_build_directories.assert_called_once
    assert not mock_default_build_component.called
    assert mock_subprocess_run.called


def test_copy_artifacts_and_update_uris_no_manifest_in_recipe(mocker):
    # Nothing to copy if manifest file doesnt exist
    # recipe with no manifest key

    import gdk.commands.component.build as build

    zip_build_path = Path("zip-build").resolve()
    mock_build_info = mocker.patch(
        "gdk.commands.component.build._get_build_folder_by_build_system", return_value=zip_build_path
    )
    mock_iter_dir_list = [Path("this-recipe-uri-not-exists.sh").resolve()]
    mock_shutil_copy = mocker.patch("shutil.copy")
    mock_glob = mocker.patch("pathlib.Path.iterdir", return_value=mock_iter_dir_list)

    modify_build = build.project_config
    modify_build["parsed_component_recipe"] = {
        "RecipeFormatVersion": "2020-01-25",
        "ComponentName": "com.example.HelloWorld",
        "ComponentVersion": "1.0.0",
        "ComponentDescription": "My first Greengrass component.",
        "ComponentPublisher": "Amazon",
        "ComponentConfiguration": {"DefaultConfiguration": {"Message": "world"}},
    }
    build.copy_artifacts_and_update_uris()
    assert not mock_shutil_copy.called
    assert not mock_build_info.called
    assert not mock_glob.called


def test_copy_artifacts_and_update_uris_no_artifacts_in_recipe(mocker):
    # Nothing to copy if artifacts in recipe manifest don't exist

    import gdk.commands.component.build as build

    zip_build_path = Path("zip-build").resolve()
    mock_build_info = mocker.patch(
        "gdk.commands.component.build._get_build_folder_by_build_system", return_value=zip_build_path
    )
    mock_iter_dir_list = Path("this-recipe-uri-not-exists.sh").resolve()
    mock_shutil_copy = mocker.patch("shutil.copy")
    mock_glob = mocker.patch("pathlib.Path.glob", return_value=mock_iter_dir_list)

    modify_build = build.project_config
    modify_build["parsed_component_recipe"] = {
        "RecipeFormatVersion": "2020-01-25",
        "ComponentName": "com.example.HelloWorld",
        "ComponentVersion": "1.0.0",
        "ComponentDescription": "My first Greengrass component.",
        "ComponentPublisher": "Amazon",
        "ComponentConfiguration": {"DefaultConfiguration": {"Message": "world"}},
        "Manifests": [
            {
                "Platform": {"os": "linux"},
                "Lifecycle": {"Run": "python3 -u {artifacts:path}/hello_world.py '{configuration:/Message}'"},
            }
        ],
    }

    build.copy_artifacts_and_update_uris()
    assert not mock_shutil_copy.called
    assert mock_build_info.called
    assert not mock_glob.called


def test_copy_artifacts_and_update_uris_no_artifact_uri_in_recipe(mocker):
    # Nothing to copy if artifact uri don't exist in the recipe.

    import gdk.commands.component.build as build

    zip_build_path = Path("zip-build").resolve()
    mock_build_info = mocker.patch(
        "gdk.commands.component.build._get_build_folder_by_build_system", return_value=zip_build_path
    )
    mock_iter_dir_list = Path("this-recipe-uri-not-exists.sh").resolve()
    mock_shutil_copy = mocker.patch("shutil.copy")
    mock_glob = mocker.patch("pathlib.Path.glob", return_value=mock_iter_dir_list)

    modify_build = build.project_config
    modify_build["parsed_component_recipe"] = {
        "RecipeFormatVersion": "2020-01-25",
        "ComponentName": "com.example.HelloWorld",
        "ComponentVersion": "1.0.0",
        "ComponentDescription": "My first Greengrass component.",
        "ComponentPublisher": "Amazon",
        "ComponentConfiguration": {"DefaultConfiguration": {"Message": "world"}},
        "Manifests": [
            {
                "Platform": {"os": "linux"},
                "Lifecycle": {"Run": "python3 -u {artifacts:path}/hello_world.py '{configuration:/Message}'"},
                "Artifacts": [{}],
            }
        ],
    }

    build.copy_artifacts_and_update_uris()
    assert not mock_shutil_copy.called
    assert mock_build_info.called
    assert not mock_glob.called


def test_copy_artifacts_and_update_uris_docker_uri_in_recipe(mocker):
    # Nothing to copy if artifact uri don't exist in the recipe.

    import gdk.commands.component.build as build

    zip_build_path = Path("zip-build").resolve()
    mock_build_info = mocker.patch(
        "gdk.commands.component.build._get_build_folder_by_build_system", return_value=zip_build_path
    )
    mock_iter_dir_list = Path("this-recipe-uri-not-exists.sh").resolve()
    mock_shutil_copy = mocker.patch("shutil.copy")
    mock_glob = mocker.patch("pathlib.Path.glob", return_value=mock_iter_dir_list)

    modify_build = build.project_config
    modify_build["parsed_component_recipe"] = {
        "RecipeFormatVersion": "2020-01-25",
        "ComponentName": "com.example.HelloWorld",
        "ComponentVersion": "1.0.0",
        "ComponentDescription": "My first Greengrass component.",
        "ComponentPublisher": "Amazon",
        "ComponentConfiguration": {"DefaultConfiguration": {"Message": "world"}},
        "Manifests": [
            {
                "Platform": {"os": "linux"},
                "Lifecycle": {"Run": "python3 -u {artifacts:path}/hello_world.py '{configuration:/Message}'"},
                "Artifacts": [{"URI": "docker:uri"}],
            }
        ],
    }

    build.copy_artifacts_and_update_uris()
    assert not mock_shutil_copy.called

    assert mock_build_info.called
    assert not mock_glob.called


def test_copy_artifacts_and_update_uris_mix_uri_in_recipe(mocker):
    # Nothing to copy if artifact uri don't exist in the recipe.

    import gdk.commands.component.build as build

    zip_build_path = Path("zip-build").resolve()
    mock_build_info = mocker.patch(
        "gdk.commands.component.build._get_build_folder_by_build_system", return_value={zip_build_path}
    )
    mock_iter_dir_list = [Path("hello_world.py").resolve()]
    mock_shutil_copy = mocker.patch("shutil.copy")
    mock_glob = mocker.patch("pathlib.Path.glob", return_value=mock_iter_dir_list)

    modify_build = build.project_config
    modify_build["parsed_component_recipe"] = {
        "RecipeFormatVersion": "2020-01-25",
        "ComponentName": "com.example.HelloWorld",
        "ComponentVersion": "1.0.0",
        "ComponentDescription": "My first Greengrass component.",
        "ComponentPublisher": "Amazon",
        "ComponentConfiguration": {"DefaultConfiguration": {"Message": "world"}},
        "Manifests": [
            {
                "Platform": {"os": "linux"},
                "Lifecycle": {"Run": "python3 -u {artifacts:path}/hello_world.py '{configuration:/Message}'"},
                "Artifacts": [{"URI": "docker:uri"}, {"URI": "s3://hello_world.py"}],
            }
        ],
    }

    build.copy_artifacts_and_update_uris()
    mock_shutil_copy.assert_called_with(Path("hello_world.py").resolve(), json_values["gg_build_component_artifacts_dir"])
    assert mock_build_info.called
    mock_glob.assert_called_with("hello_world.py")


def test_get_build_folder_by_build_system_maven(mocker):
    import gdk.commands.component.build as build

    dummy_paths = [Path("/").joinpath("path1"), Path("/").joinpath(*["path1", "path2"])]
    mock_get_build_folders = mocker.patch("gdk.commands.component.build.get_build_folders", return_value=dummy_paths)
    build.project_config["component_build_config"] = {"build_system": "maven"}
    maven_build_paths = build._get_build_folder_by_build_system()
    assert maven_build_paths == dummy_paths
    mock_get_build_folders.assert_any_call(["target"], "pom.xml")


def test_get_build_folder_by_build_system_gradle(mocker):
    import gdk.commands.component.build as build

    dummy_paths = [Path("/").joinpath("path1"), Path("/").joinpath(*["path1", "path2"])]
    mock_get_build_folders = mocker.patch("gdk.commands.component.build.get_build_folders", return_value=dummy_paths)
    build.project_config["component_build_config"] = {"build_system": "gradle"}
    gradle_build_paths = build._get_build_folder_by_build_system()
    assert gradle_build_paths == dummy_paths
    mock_get_build_folders.assert_any_call(["build", "libs"], "build.gradle")


def test_get_build_folders_maven(mocker):
    import gdk.commands.component.build as build

    dummy_build_file_paths = [Path("/").joinpath("path1"), Path("/").joinpath(*["path1", "path2"])]
    dummy_build_folder_paths = [
        Path("/").joinpath("path1"),
        Path("/").joinpath(*["path1", "path2"]),
        Path("/").joinpath(*["path3", "path1"]),
    ]

    def get_files(*args, **kwargs):
        if args[0] == "pom.xml":
            return dummy_build_file_paths
        else:
            return dummy_build_folder_paths

    mock_rglob = mocker.patch("pathlib.Path.rglob", side_effect=get_files)
    build.project_config["component_build_config"] = {"build_system": "maven"}
    maven_b_paths = build.get_build_folders(["target"], "pom.xml")
    mock_rglob.assert_any_call("pom.xml")
    mock_rglob.assert_any_call("target")
    assert maven_b_paths == {Path("/").joinpath(*["target"]), Path("/").joinpath(*["path1", "target"])}


def test_get_build_folders_gradle(mocker):
    import gdk.commands.component.build as build

    dummy_build_file_paths = [Path("/").joinpath("path1"), Path("/").joinpath(*["path1", "path2"])]
    dummy_build_folder_paths = [
        Path("/").joinpath("path1"),
        Path("/").joinpath(*["path1", "path2"]),
        Path("/").joinpath(*["path3", "path1"]),
    ]

    def get_files(*args, **kwargs):
        if args[0] == "build.gradle":
            return dummy_build_file_paths
        else:
            return dummy_build_folder_paths

    mock_rglob = mocker.patch("pathlib.Path.rglob", side_effect=get_files)
    build.project_config["component_build_config"] = {"build_system": "gradle"}
    maven_b_paths = build.get_build_folders(["build", "libs"], "build.gradle")
    mock_rglob.assert_any_call("build.gradle")
    mock_rglob.assert_any_call(str(Path(".").joinpath(*["build", "libs"])))
    assert maven_b_paths == {Path("/").joinpath(*["build", "libs"]), Path("/").joinpath(*["path1", "build", "libs"])}
