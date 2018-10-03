import json
import logging

import pkg_resources
import requests
import yaml
from jsonschema import Draft7Validator, RefResolver
from jsonschema.exceptions import ValidationError

LOG = logging.getLogger(__name__)


TIMEOUT_IN_SECONDS = 10


def make_validator(schema, base_uri=None, timeout=TIMEOUT_IN_SECONDS):
    if not base_uri:
        base_uri = Draft7Validator.ID_OF(schema)

    def get_with_timeout(uri):
        return requests.get(uri, timeout=timeout).json()

    resolver = RefResolver(
        base_uri=base_uri,
        referrer=schema,
        handlers={"http": get_with_timeout, "https": get_with_timeout},
    )
    return Draft7Validator(schema, resolver=resolver)


def load_resource_spec(resource_spec_file):
    """Load a resource provider definition from a file, and validate it."""
    try:
        resource_spec = yaml.safe_load(resource_spec_file)
    except yaml.YAMLError as e:
        LOG.error("Could not load the resource provider definition: %s", e)
        raise
        # TODO: error handling, decode errors have 'msg', 'doc', 'pos'

    with pkg_resources.resource_stream(
        __name__, "data/schema/provider.definition.schema.v1.json"
    ) as f:
        resource_spec_schema = json.load(f)

    validator = make_validator(resource_spec_schema)
    try:
        validator.validate(resource_spec)
    except ValidationError as e:
        LOG.error(
            "The resource provider definition is invalid: %s", e.message  # noqa: B306
        )
        raise

    return resource_spec


def load_project_settings(plugin, project_settings_file):
    """Load language-specific project settings from a file, merge them into
    the default project settings, and validate the result.

    ``project_settings_file`` can be ``None``.
    """
    project_settings = yaml.safe_load(plugin.project_settings_defaults())

    if project_settings_file:
        try:
            project_settings_user = yaml.safe_load(project_settings_file)
        except yaml.YAMLError as e:
            LOG.error("Could not load the project settings: %s", e)
            raise
            # TODO: error handling, decode errors have 'msg', 'doc', 'pos'
        else:
            project_settings.update(project_settings_user)
    else:
        LOG.warning(
            "Using default project settings. Provide custom project settings "
            "to further customize code generation."
        )

    validator = make_validator(plugin.project_settings_schema())
    try:
        validator.validate(project_settings)
    except ValidationError as e:
        LOG.error("The project settings are invalid: %s", e.message)  # noqa: B306
        raise  # TODO: error handling

    return project_settings
