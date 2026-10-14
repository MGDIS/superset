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
from sqlalchemy.orm.session import Session

from superset import db
from superset.utils.core import DatasourceType


@pytest.fixture
def session_with_data(session: Session):
    from superset.connectors.sqla.models import SqlaTable, TableColumn
    from superset.models.core import Database
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice
    from superset.models.sql_lab import SavedQuery

    engine = session.get_bind()
    SqlaTable.metadata.create_all(engine)  # pylint: disable=no-member

    slice_obj = Slice(
        id=1,
        datasource_id=1,
        datasource_type=DatasourceType.TABLE,
        datasource_name="tmp_perm_table",
        slice_name="slice_name",
    )

    database = Database(database_name="my_database", sqlalchemy_uri="postgresql://")

    [  # noqa: F841
        TableColumn(column_name="a", type="INTEGER"),
    ]

    saved_query = SavedQuery(
        label="test_query", database=database, sql="select * from foo"
    )

    dashboard_obj = Dashboard(
        id=100,
        dashboard_title="test_dashboard",
        slug="test_slug",
        slices=[],
        published=True,
    )

    session.add(slice_obj)
    session.add(database)
    session.add(saved_query)
    session.add(dashboard_obj)
    session.commit()
    return session


def test_create_command_success(session_with_data: Session, mocker: MockerFixture):
    from superset.commands.tag.create import CreateCustomTagWithRelationshipsCommand
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice
    from superset.models.sql_lab import SavedQuery
    from superset.tags.models import ObjectType, TaggedObject

    # Define a list of objects to tag
    query = db.session.query(SavedQuery).first()
    chart = db.session.query(Slice).first()
    dashboard = db.session.query(Dashboard).first()

    mocker.patch(
        "superset.security.SupersetSecurityManager.is_admin", return_value=True
    )
    mocker.patch("superset.daos.chart.ChartDAO.find_by_id", return_value=chart)
    mocker.patch("superset.daos.query.SavedQueryDAO.find_by_id", return_value=query)

    objects_to_tag = [
        (ObjectType.query, query.id),
        (ObjectType.chart, chart.id),
        (ObjectType.dashboard, dashboard.id),
    ]

    CreateCustomTagWithRelationshipsCommand(
        data={"name": "test_tag", "objects_to_tag": objects_to_tag}
    ).run()

    assert len(db.session.query(TaggedObject).all()) == len(objects_to_tag)
    for object_type, object_id in objects_to_tag:
        assert (
            db.session.query(TaggedObject)
            .filter(
                TaggedObject.object_type == object_type,
                TaggedObject.object_id == object_id,
            )
            .one_or_none()
            is not None
        )


def test_create_command_existing_name_rejected(
    session_with_data: Session, mocker: MockerFixture
):
    from superset.commands.tag.create import CreateCustomTagWithRelationshipsCommand
    from superset.commands.tag.exceptions import TagInvalidError
    from superset.daos.tag import TagDAO
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice
    from superset.models.sql_lab import SavedQuery
    from superset.tags.models import ObjectType, TaggedObject

    query = db.session.query(SavedQuery).first()
    chart = db.session.query(Slice).first()
    dashboard = db.session.query(Dashboard).first()

    mocker.patch(
        "superset.security.SupersetSecurityManager.is_admin", return_value=True
    )
    mocker.patch("superset.daos.chart.ChartDAO.find_by_id", return_value=chart)
    mocker.patch("superset.daos.query.SavedQueryDAO.find_by_id", return_value=query)

    objects_to_tag = [
        (ObjectType.query, query.id),
        (ObjectType.chart, chart.id),
        (ObjectType.dashboard, dashboard.id),
    ]

    CreateCustomTagWithRelationshipsCommand(
        data={
            "name": "test_tag",
            "description": "original",
            "objects_to_tag": objects_to_tag,
        }
    ).run()
    assert len(db.session.query(TaggedObject).all()) == len(objects_to_tag)

    with pytest.raises(TagInvalidError) as excinfo:
        CreateCustomTagWithRelationshipsCommand(
            data={
                "name": "test_tag",
                "description": "overwritten",
                "objects_to_tag": [],
            }
        ).run()

    assert excinfo.value.normalized_messages() == {
        "name": ["A tag with this name already exists"]
    }
    assert len(db.session.query(TaggedObject).all()) == len(objects_to_tag)
    assert TagDAO.find_by_name("test_tag").description == "original"


def test_create_command_bulk_existing_name_keeps_description(
    session_with_data: Session, mocker: MockerFixture
):
    from superset.commands.tag.create import CreateCustomTagWithRelationshipsCommand
    from superset.daos.tag import TagDAO
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice
    from superset.tags.models import ObjectType

    chart = db.session.query(Slice).first()
    dashboard = db.session.query(Dashboard).first()

    mocker.patch(
        "superset.security.SupersetSecurityManager.is_admin", return_value=True
    )
    mocker.patch("superset.daos.chart.ChartDAO.find_by_id", return_value=chart)
    mocker.patch(
        "superset.daos.dashboard.DashboardDAO.find_by_id", return_value=dashboard
    )

    CreateCustomTagWithRelationshipsCommand(
        data={
            "name": "test_tag",
            "description": "original",
            "objects_to_tag": [(ObjectType.chart, chart.id)],
        }
    ).run()
    CreateCustomTagWithRelationshipsCommand(
        data={
            "name": "test_tag",
            "description": None,
            "objects_to_tag": [(ObjectType.dashboard, dashboard.id)],
        },
        bulk_create=True,
    ).run()

    assert TagDAO.find_by_name("test_tag").description == "original"


def test_create_command_bulk_existing_name_adds_to_existing_tag(
    session_with_data: Session, mocker: MockerFixture
):
    from superset.commands.tag.create import CreateCustomTagWithRelationshipsCommand
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice
    from superset.tags.models import ObjectType, TaggedObject

    chart = db.session.query(Slice).first()
    dashboard = db.session.query(Dashboard).first()

    mocker.patch(
        "superset.security.SupersetSecurityManager.is_admin", return_value=True
    )
    mocker.patch("superset.daos.chart.ChartDAO.find_by_id", return_value=chart)
    mocker.patch(
        "superset.daos.dashboard.DashboardDAO.find_by_id", return_value=dashboard
    )

    CreateCustomTagWithRelationshipsCommand(
        data={"name": "test_tag", "objects_to_tag": [(ObjectType.chart, chart.id)]}
    ).run()
    CreateCustomTagWithRelationshipsCommand(
        data={
            "name": "test_tag",
            "objects_to_tag": [(ObjectType.dashboard, dashboard.id)],
        },
        bulk_create=True,
    ).run()

    tagged = {
        (obj.object_type, obj.object_id) for obj in db.session.query(TaggedObject)
    }
    assert tagged == {
        (ObjectType.chart, chart.id),
        (ObjectType.dashboard, dashboard.id),
    }
