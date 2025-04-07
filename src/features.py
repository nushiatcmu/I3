"""Declarative feature and anchor definitions for the movie‑streaming demo."""
from feathr import (
    HdfsSource,
    Feature,
    FeatureAnchor,
    TypedKey,
    ValueType,
)

# ---------------------------------------------------------------------------
# 1. Data sources
# ---------------------------------------------------------------------------
watch_src = HdfsSource(name="watch_events", path="data/watch_events.parquet")
users_src = HdfsSource(name="users", path="data/users.parquet")

# ---------------------------------------------------------------------------
# 2. Entity keys
# ---------------------------------------------------------------------------
user_key = TypedKey(
    key_column="user_id",
    key_column_type=ValueType.INT32,
    description="User identifier",
)

# ---------------------------------------------------------------------------
# 3. Feature specs
# ---------------------------------------------------------------------------
f_watch_30d = Feature(
    name="watch_time_30d",
    key=user_key,
    feature_type="numeric",
    transform_expr="SUM(watch_time)",
    aggregation_interval="30d",
    window="30d",
)

f_lifetime = Feature(
    name="lifetime_days",
    key=user_key,
    transform_expr="DATEDIFF('day', CURRENT_DATE, signup_date)",
)

# ---------------------------------------------------------------------------
# 4. Anchors
# ---------------------------------------------------------------------------
anchor_watch = FeatureAnchor(
    name="watch_anchor",
    source=watch_src,
    features=[f_watch_30d],
)

anchor_users = FeatureAnchor(
    name="user_anchor",
    source=users_src,
    features=[f_lifetime],
)
