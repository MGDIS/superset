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

from collections.abc import Iterator

import pytest
from sqlalchemy.orm.session import Session

from superset.utils.core import DatasourceType
from tests.unit_tests.conftest import with_feature_flags


@pytest.fixture
def session_with_data(session: Session) -> Iterator[Session]:
    from superset.models.slice import Slice

    engine = session.get_bind()
    Slice.metadata.create_all(engine)  # pylint: disable=no-member

    slice_obj = Slice(
        id=1,
        datasource_id=1,
        datasource_type=DatasourceType.TABLE,
        datasource_name="tmp_perm_table",
        slice_name="slice_name",
    )
    session.add(slice_obj)

    session.commit()
    yield session
    session.rollback()


def test_slice_find_by_id_skip_base_filter(session_with_data: Session) -> None:
    from superset.daos.chart import ChartDAO
    from superset.models.slice import Slice

    result = ChartDAO.find_by_id(1, skip_base_filter=True)

    assert result
    assert 1 == result.id
    assert "slice_name" == result.slice_name
    assert isinstance(result, Slice)


def test_datasource_find_by_id_skip_base_filter_not_found(
    session: Session,
) -> None:
    from superset.daos.chart import ChartDAO

    result = ChartDAO.find_by_id(125326326, skip_base_filter=True)
    assert result is None


def test_add_favorite(session: Session) -> None:
    from superset.daos.chart import ChartDAO

    chart = ChartDAO.find_by_id(1, skip_base_filter=True)
    if not chart:
        return
    assert len(ChartDAO.favorited_ids([chart])) == 0

    ChartDAO.add_favorite(chart)
    assert len(ChartDAO.favorited_ids([chart])) == 1

    ChartDAO.add_favorite(chart)
    assert len(ChartDAO.favorited_ids([chart])) == 1


def test_remove_favorite(session: Session) -> None:
    from superset.daos.chart import ChartDAO

    chart = ChartDAO.find_by_id(1, skip_base_filter=True)
    if not chart:
        return
    assert len(ChartDAO.favorited_ids([chart])) == 0

    ChartDAO.add_favorite(chart)
    assert len(ChartDAO.favorited_ids([chart])) == 1

    ChartDAO.remove_favorite(chart)
    assert len(ChartDAO.favorited_ids([chart])) == 0

    ChartDAO.remove_favorite(chart)
    assert len(ChartDAO.favorited_ids([chart])) == 0


@with_feature_flags(DATASET_RBAC=True)
def test_find_all_returns_owned_charts(session: Session) -> None:
    from flask_appbuilder.security.sqla.models import User

    from superset.connectors.sqla.models import SqlaTable
    from superset.daos.chart import ChartDAO
    from superset.models.core import Database
    from superset.models.slice import Slice
    from superset.utils.core import override_user

    # Create the tables of the models in the test database
    SqlaTable.metadata.create_all(session.get_bind())  # pylint: disable=no-member

    # Create the user that owns a chart
    owner = User(
        username="chart_owner",
        first_name="Alice",
        last_name="Doe",
        email="adoe@example.org",
    )

    # Create one dataset for the two charts
    database = Database(database_name="my_database", sqlalchemy_uri="sqlite://")
    table = SqlaTable(table_name="my_table", database=database)

    # Add a chart that the user owns and a chart without owner
    for name, owners in (("owned_chart", [owner]), ("other_chart", [])):
        session.add(
            Slice(
                slice_name=name,
                table=table,
                datasource_type=DatasourceType.TABLE,
                owners=owners,
            )
        )
    session.flush()

    # The user has no database or dataset access
    # The user must see only the chart that the user owns
    with override_user(owner):
        assert [chart.slice_name for chart in ChartDAO.find_all()] == ["owned_chart"]
