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

from sqlalchemy.orm.session import Session

from superset.daos.dataset import DatasetDAO
from superset.sql_parse import Table


def test_validate_update_uniqueness(session: Session) -> None:
    """
    Test the `validate_update_uniqueness` static method.

    In particular, allow datasets with the same name in the same database as long as they
    are in different schemas
    """  # noqa: E501
    from superset import db
    from superset.connectors.sqla.models import SqlaTable
    from superset.models.core import Database

    SqlaTable.metadata.create_all(session.get_bind())

    database = Database(
        database_name="my_db",
        sqlalchemy_uri="sqlite://",
    )
    dataset1 = SqlaTable(
        table_name="my_dataset",
        schema="main",
        database=database,
    )
    dataset2 = SqlaTable(
        table_name="my_dataset",
        schema="dev",
        database=database,
    )
    db.session.add_all([database, dataset1, dataset2])
    db.session.flush()

    assert (
        DatasetDAO.validate_update_uniqueness(
            database=database,
            table=Table(dataset1.table_name, dataset1.schema),
            dataset_id=dataset1.id,
        )
        is True
    )

    assert (
        DatasetDAO.validate_update_uniqueness(
            database=database,
            table=Table(dataset1.table_name, dataset2.schema),
            dataset_id=dataset1.id,
        )
        is False
    )

    assert (
        DatasetDAO.validate_update_uniqueness(
            database=database,
            table=Table(dataset1.table_name),
            dataset_id=dataset1.id,
        )
        is True
    )


def test_override_columns_preserves_pks_and_ignores_payload_id(
    session: Session,
) -> None:
    from superset import db
    from superset.connectors.sqla.models import SqlaTable, TableColumn
    from superset.models.core import Database

    SqlaTable.metadata.create_all(session.get_bind())
    database = Database(database_name="ov_db", sqlalchemy_uri="sqlite://")
    table = SqlaTable(table_name="ov_t", schema="main", database=database)
    table.columns = [TableColumn(column_name="a"), TableColumn(column_name="b")]
    db.session.add_all([database, table])
    db.session.flush()
    a_id = next(c.id for c in table.columns if c.column_name == "a")

    DatasetDAO._override_columns(
        table,
        [
            {"column_name": "a", "id": a_id + 9999, "verbose_name": "A!"},
            {"column_name": "c"},
        ],
    )
    db.session.flush()

    cols = db.session.query(TableColumn).filter_by(table_id=table.id).all()
    by_name = {c.column_name: c for c in cols}
    assert set(by_name) == {"a", "c"}
    assert by_name["a"].id == a_id
    assert by_name["a"].verbose_name == "A!"


def test_override_columns_rename_flushes_delete_before_insert(
    session: Session,
) -> None:
    from superset import db
    from superset.connectors.sqla.models import SqlaTable, TableColumn
    from superset.models.core import Database

    SqlaTable.metadata.create_all(session.get_bind())
    database = Database(database_name="ov_db2", sqlalchemy_uri="sqlite://")
    table = SqlaTable(table_name="ov_t2", schema="main", database=database)
    table.columns = [TableColumn(column_name="old")]
    db.session.add_all([database, table])
    db.session.flush()

    DatasetDAO._override_columns(table, [{"column_name": "new"}])
    db.session.flush()
    cols = db.session.query(TableColumn).filter_by(table_id=table.id).all()
    assert [c.column_name for c in cols] == ["new"]


def test_override_columns_keeps_metadata_when_payload_omits_it(
    session: Session,
) -> None:
    from superset import db
    from superset.connectors.sqla.models import SqlaTable, TableColumn
    from superset.models.core import Database

    SqlaTable.metadata.create_all(session.get_bind())
    database = Database(database_name="ov_db3", sqlalchemy_uri="sqlite://")
    table = SqlaTable(table_name="ov_t3", schema="main", database=database)
    table.columns = [
        TableColumn(
            column_name="a", verbose_name="Label A", description="d", groupby=False
        )
    ]
    db.session.add_all([database, table])
    db.session.flush()

    DatasetDAO.update_columns(
        table,
        [{"column_name": "a", "type": "INTEGER", "is_dttm": False}],
        override_columns=True,
    )
    db.session.flush()
    col = db.session.query(TableColumn).filter_by(table_id=table.id).one()
    assert col.verbose_name == "Label A"
    assert col.description == "d"
    assert col.groupby is False
    assert col.type == "INTEGER"
