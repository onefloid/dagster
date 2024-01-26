import os
from pathlib import Path

import pytest
import yaml
from dagster import AssetKey
from dagster_embedded_elt.sling.asset_decorator import sling_assets
from dagster_embedded_elt.sling.sling_replication import SlingReplicationParam

replication_path = Path(__file__).joinpath("..", "sling_replication.yaml").resolve()
with replication_path.open("r") as f:
    replication = yaml.safe_load(f)


@pytest.mark.parametrize(
    "replication", [replication, replication_path, os.fspath(replication_path)]
)
def test_replication_argument(replication: SlingReplicationParam):
    @sling_assets(replication=replication)
    def my_sling_assets():
        ...

    assert my_sling_assets.keys == {
        AssetKey.from_user_string(key)
        for key in [
            "target/public/accounts",
            "target/public/foo_users",
            "target/public/Transactions",
            "target/public/all_users",
            "target/public/finance_departments_old",
        ]
    }
