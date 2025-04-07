"""Entry‑point script to register and materialise features offline & online."""
from datetime import datetime
from feathr import FeathrClient, ObservationSettings

from features import (
    anchor_watch,
    anchor_users,
    f_watch_30d,
    f_lifetime,
)


def main() -> None:
    client = FeathrClient(config_path="configs/feathr_config.yaml")

    # ---------------------------------------------------------------------
    # 1. Register anchors & features in the registry
    # ---------------------------------------------------------------------
    client.register_features(anchor_watch, anchor_users)

    # ---------------------------------------------------------------------
    # 2. Backfill offline features (Parquet/Delta)
    # ---------------------------------------------------------------------
    client.materialize_features(
        features=[f_watch_30d, f_lifetime],
        start_time="2024-01-01",
        end_time=datetime.utcnow().strftime("%Y-%m-%d"),
    )

    # ---------------------------------------------------------------------
    # 3. Push latest feature values to the online store (Redis)
    # ---------------------------------------------------------------------
    client.materialize_features_online(features=[f_watch_30d, f_lifetime])

    # ---------------------------------------------------------------------
    # 4. Example: fetch point‑in‑time training dataset
    # ---------------------------------------------------------------------
    obs = ObservationSettings(
        obs_path="data/labels.parquet",
        timestamp_column="ts",
    )
    training_df = client.get_offline_features(
        observation_settings=obs,
        features=[f_watch_30d, f_lifetime],
    )
    print("Training dataset rows:", training_df.count())

    # ---------------------------------------------------------------------
    # 5. Example: fetch online features for inference
    # ---------------------------------------------------------------------
    online_resp = client.get_online_features(
        feature_names=["watch_time_30d", "lifetime_days"],
        key={"user_id": 42},
    )
    print("Online lookup:", online_resp)


if __name__ == "__main__":
    main()
