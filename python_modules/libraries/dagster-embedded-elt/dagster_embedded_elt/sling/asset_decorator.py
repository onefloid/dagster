import re
from typing import Any, Callable, Iterable, Mapping, Optional

from dagster import (
    AssetKey,
    AssetsDefinition,
    AssetSpec,
    BackfillPolicy,
    FreshnessPolicy,
    PartitionsDefinition,
    multi_asset,
)
from dagster._annotations import public
from dagster._core.definitions.auto_materialize_policy import AutoMaterializePolicy

from dagster_embedded_elt.sling.sling_replication import SlingReplicationParam, validate_replication


def get_streams_from_replication(replication_config: Mapping[str, Any]) -> Iterable[str]:
    """Returns the set of streams from a Sling replication config."""
    keys = []

    for key, value in replication_config["streams"].items():
        if isinstance(value, dict):
            asset_key_config = value.get("meta", {}).get("dagster", {}).get("asset_key", [])
            keys.append(asset_key_config if asset_key_config else key)
        else:
            keys.append(key)
    return keys


class DagsterSlingTranslator:
    @public
    @classmethod
    def sanitize_stream_name(cls, stream_name: str) -> str:
        """A function that takes a stream name from a Sling replication config and returns a
        sanitized name for the stream.
        By default, this removes any non-alphanumeric characters from the stream name and replaces
        them with underscores, while removing any double quotes.
        """
        return re.sub(r"[^a-zA-Z0-9_.]", "_", stream_name.replace('"', ""))

    @public
    @classmethod
    def get_asset_key_for_target(cls, stream_name: str, target_prefix: str = "target") -> AssetKey:
        """A function that takes a stream name from a Sling replication config and returns a
        Dagster AssetKey.

        By default, this returns the target_prefix concatenated with the stream name. For example, a stream
        named "public.accounts" will create an AssetKey named "target_public_accounts".

        Override this function to customize how to map a Sling stream to a Dagster AssetKey.
        Alternatively, you can provide metadata in your Sling replication config to specify the
        Dagster AssetKey for a stream as follows:

        public.users:
           meta:
             dagster:
               asset_key: "mydb_users"

        Args:
            stream_name (str): The name of the stream.

        Returns:
            AssetKey: The Dagster AssetKey for the replication stream.

        Examples:
            Using a custom mapping for streams:

            class CustomSlingTranslator(DagsterSlingTranslator):
                @classmethod
                def get_asset_key_for_target(cls, stream_name: str) -> AssetKey:
                    map = {"stream1": "asset1", "stream2": "asset2"}
                    return AssetKey(map[stream_name])
        """
        components = cls.sanitize_stream_name(stream_name).split(".")
        return AssetKey([target_prefix] + components)

    @public
    @classmethod
    def get_deps_asset_key(cls, stream_name: str) -> AssetKey:
        """A function that takes a stream name from a Sling replication config and returns a
        Dagster AssetKey for the dependencies of the replication stream.

        By default, this returns the stream name. For example, a stream
        named "public.accounts" will create an AssetKey named "target_public_accounts" and a
        depenency AssetKey named "public_accounts".

        Override this function to customize how to map a Sling stream to a Dagster AssetKey.
        Alternatively, you can provide metadata in your Sling replication config to specify the
        Dagster AssetKey for a stream as follows:

        public.users:
           meta:
             dagster:
               deps: "sourcedb_users"

        Args:
            stream_name (str): The name of the stream.

        Returns:
            AssetKey: The Dagster AssetKey dependency for the replication stream.

        Examples:
            Using a custom mapping for streams:

            class CustomSlingTranslator(DagsterSlingTranslator):
                @classmethod
                def get_deps_asset_key(cls, stream_name: str) -> AssetKey:
                    map = {"stream1": "asset1", "stream2": "asset2"}
                    return AssetKey(map[stream_name])


        """
        components = cls.sanitize_stream_name(stream_name).split(".")
        return AssetKey(components)


def sling_assets(
    *,
    replication_config: SlingReplicationParam,
    dagster_sling_translator: DagsterSlingTranslator = DagsterSlingTranslator(),
    name: Optional[str] = None,
    partitions_def: Optional[PartitionsDefinition] = None,
    backfill_policy: Optional[BackfillPolicy] = None,
    op_tags: Optional[Mapping[str, Any]] = None,
    group_name: Optional[str] = None,
    code_version: Optional[str] = None,
    freshness_policy: Optional[FreshnessPolicy] = None,
    auto_materialize_policy: Optional[AutoMaterializePolicy] = None,
) -> Callable[..., AssetsDefinition]:
    """Create a definition for how to materialize a Sling replication stream as a Dagster Asset, as
    described by a Sling replication config.

    Args:
        replication_config: SlingReplicationParam: A path to a Sling replication config, or a dictionary of a replication config.
        dagster_sling_translator: DagsterSlingTranslator: Allows customization of how to map a Sling stream to a Dagster AssetKey.
        deps: Optional[Iterable[CoercibleToAssetDep]]: A list of dependencies for these assets
        name: Optional[str]: The name of the asset.
        partitions_def: Optional[PartitionsDefinition]: The partitions definition for this asset.
        backfill_policy: Optional[BackfillPolicy]: The backfill policy for this asset.
        op_tags: Optional[Mapping[str, Any]]: The tags for this asset.
        group_name: Optional[str]: The group name for this asset.
        code_version: Optional[str]: The code version for this asset.
        freshness_policy: Optional[FreshnessPolicy]: The freshness policy for this asset.
        auto_materialize_policy: Optional[AutoMaterializePolicy]: The auto materialize policy for this asset.

    Examples:
        # TODO: Add examples once API is complete
    """
    replication_config = validate_replication(replication_config)
    streams = get_streams_from_replication(replication_config)

    specs: list[AssetSpec] = []
    for stream in streams:
        specs.append(
            AssetSpec(
                key=dagster_sling_translator.get_asset_key_for_target(stream),
                deps=dagster_sling_translator.get_deps_asset_key(stream),
                group_name=group_name,
                code_version=code_version,
                freshness_policy=freshness_policy,
                auto_materialize_policy=auto_materialize_policy,
            )
        )

    def inner(fn) -> AssetsDefinition:
        asset_definition = multi_asset(
            name=name,
            compute_kind="sling",
            partitions_def=partitions_def,
            can_subset=False,
            op_tags=op_tags,
            backfill_policy=backfill_policy,
            specs=specs,
        )(fn)

        return asset_definition

    return inner
