# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import pytest
from pytest_mock import MockerFixture

from superset.connectors.sqla.utils import (
    get_columns_description,
    get_virtual_table_metadata,
)
from superset.db_engine_specs.exceptions import SupersetDBAPIConnectionError
from superset.exceptions import OAuth2RedirectError, SupersetSecurityException


# Returns column descriptions when given valid database, catalog, schema, and query
def test_returns_column_descriptions(mocker: MockerFixture) -> None:
    database = mocker.MagicMock()
    cursor = mocker.MagicMock()

    result_set = mocker.MagicMock()
    db_engine_spec = mocker.MagicMock()

    CURSOR_DESCR = (  # noqa: N806
        ("foo", "string"),
        ("bar", "string"),
        ("baz", "string"),
        ("type_generic", "string"),
        ("is_dttm", "boolean"),
    )
    cursor.description = CURSOR_DESCR

    database.get_raw_connection.return_value.__enter__.return_value.cursor.return_value = cursor  # noqa: E501
    database.db_engine_spec = db_engine_spec
    database.apply_limit_to_sql.return_value = "SELECT * FROM table LIMIT 1"
    database.mutate_sql_based_on_config.return_value = "SELECT * FROM table LIMIT 1"
    db_engine_spec.fetch_data.return_value = [("col1", "col1", "STRING", None, False)]
    db_engine_spec.get_datatype.return_value = "STRING"
    db_engine_spec.get_column_spec.return_value.is_dttm = False
    db_engine_spec.get_column_spec.return_value.generic_type = "STRING"

    mocker.patch("superset.result_set.SupersetResultSet", return_value=result_set)

    columns = get_columns_description(
        database, "catalog", "schema", "SELECT * FROM table"
    )

    assert columns == [
        {
            "column_name": "foo",
            "name": "foo",
            "type": "STRING",
            "type_generic": "STRING",
            "is_dttm": False,
        },
        {
            "column_name": "bar",
            "name": "bar",
            "type": "STRING",
            "type_generic": "STRING",
            "is_dttm": False,
        },
        {
            "column_name": "baz",
            "name": "baz",
            "type": "STRING",
            "type_generic": "STRING",
            "is_dttm": False,
        },
        {
            "column_name": "type_generic",
            "name": "type_generic",
            "type": "STRING",
            "type_generic": "STRING",
            "is_dttm": False,
        },
        {
            "column_name": "is_dttm",
            "name": "is_dttm",
            "type": "STRING",
            "type_generic": "STRING",
            "is_dttm": False,
        },
    ]


def test_get_virtual_table_metadata(mocker: MockerFixture) -> None:
    """
    Test the `get_virtual_table_metadata` function.
    """
    mocker.patch(
        "superset.connectors.sqla.utils.get_columns_description",
        return_value=[{"name": "one", "type": "INTEGER"}],
    )
    dataset = mocker.MagicMock(
        sql="with source as ( select 1 as one ) select * from source",
    )
    dataset.database.db_engine_spec.engine = "postgresql"
    dataset.get_template_processor().process_template.return_value = dataset.sql

    assert get_virtual_table_metadata(dataset) == [{"name": "one", "type": "INTEGER"}]


def test_get_virtual_table_metadata_mutating(mocker: MockerFixture) -> None:
    """
    Test the `get_virtual_table_metadata` function with mutating SQL.
    """
    dataset = mocker.MagicMock(sql="DROP TABLE sample_data")
    dataset.database.db_engine_spec.engine = "postgresql"
    dataset.get_template_processor().process_template.return_value = dataset.sql

    with pytest.raises(SupersetSecurityException) as excinfo:
        get_virtual_table_metadata(dataset)
    assert str(excinfo.value) == "Only `SELECT` statements are allowed"


def test_get_virtual_table_metadata_multiple(mocker: MockerFixture) -> None:
    """
    Test the `get_virtual_table_metadata` function with multiple statements.
    """
    dataset = mocker.MagicMock(sql="SELECT 1; SELECT 2")
    dataset.database.db_engine_spec.engine = "postgresql"
    dataset.get_template_processor().process_template.return_value = dataset.sql

    with pytest.raises(SupersetSecurityException) as excinfo:
        get_virtual_table_metadata(dataset)
    assert str(excinfo.value) == "Only single queries supported"


def test_get_columns_description_propagates_oauth2_redirect(
    mocker: MockerFixture,
) -> None:
    """
    ``get_columns_description`` wraps every exception raised while executing
    the metadata query into ``SupersetGenericDBErrorException`` -- but an
    ``OAuth2RedirectError`` raised by the driver (e.g. a database requiring
    per-user OAuth2 tokens) must reach the caller unchanged so the frontend
    can start the OAuth2 dance, instead of being flattened into an opaque
    generic DB error.
    """
    database = mocker.MagicMock()
    cursor = mocker.MagicMock()
    oauth2_error = OAuth2RedirectError("https://example.org/oauth2", "tab-id", "uri")

    database.get_raw_connection.return_value.__enter__.return_value.cursor.return_value = cursor  # noqa: E501
    database.db_engine_spec.execute.side_effect = oauth2_error

    with pytest.raises(OAuth2RedirectError):
        get_columns_description(database, "catalog", "schema", "SELECT * FROM table")


def test_get_columns_description_propagates_dbapi_error(
    mocker: MockerFixture,
) -> None:
    """
    A connection failure normalized by ``db_engine_spec.execute`` into a
    ``SupersetDBAPIConnectionError`` must also reach the caller unchanged --
    not be re-flattened into an opaque ``SupersetGenericDBErrorException`` --
    so callers like ``CreateDatasetCommand`` can let it propagate with its
    own status instead of misreporting an infra failure as bad user input.
    """
    database = mocker.MagicMock()
    cursor = mocker.MagicMock()
    connection_error = SupersetDBAPIConnectionError(
        "could not connect to server: Connection refused"
    )

    database.get_raw_connection.return_value.__enter__.return_value.cursor.return_value = cursor  # noqa: E501
    database.db_engine_spec.execute.side_effect = connection_error

    with pytest.raises(SupersetDBAPIConnectionError):
        get_columns_description(database, "catalog", "schema", "SELECT * FROM table")
