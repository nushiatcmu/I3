from feathr import (FeathrClient, HdfsSource, ObservationSettings, Feature, FeatureAnchor, TypedKey, ValueType)

watch_src = HdfsSource(name="watch_events", path="data/watch_events.parquet")
users_src = HdfsSource(name="users", path="data/users.parquet")

user_key = TypedKey(key_column="user_id", key_column_type=ValueType.INT32, description="User identifier")

f_watch_30d = Feature(name="watch_time_30d",
    key=user_key,
    feature_type="numeric",
    transform_expr="SUM(watch_time)",
    aggregation_interval="30d",
    window="30d")

f_lifetime = Feature(name="lifetime_days",
    key=user_key,
    transform_expr="DATEDIFF('day', CURRENT_DATE, signup_date)")

anchor_watch = FeatureAnchor(name="watch_anchor", source=watch_src,
                             features=[f_watch_30d])
anchor_users = FeatureAnchor(name="user_anchor", source=users_src,
                             features=[f_lifetime])

client = FeathrClient(config_path="feathr_config.yaml")
client.register_features(anchor_watch, anchor_users)

client.materialize_features(features=[f_watch_30d, f_lifetime], start_time="2024-01-01", end_time="2025-01-01")

client.materialize_features_online(features=[f_watch_30d, f_lifetime])

obs = ObservationSettings(obs_path="data/labels.parquet", timestamp_column="ts")
training_df = client.get_offline_features(observation_settings=obs, features=[f_watch_30d, f_lifetime])

online_resp = client.get_online_features(feature_names=["watch_time_30d", "lifetime_days"], key={"user_id": 42})
print(online_resp)


