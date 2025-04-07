# I3
# Feathr Movie‑Streaming Feature Store Demo

A hands‑on, end‑to‑end example that shows how to use **[Feathr](https://github.com/linkedin/feathr)** to build leakage‑free, production‑ready features for a movie‑streaming churn‑prediction model.

The repo demonstrates:

* Declarative feature definitions in Python
* Automatic point‑in‑time joins for offline training datasets
* Turn‑key online serving backed by **Redis**
* CI/CD hooks (GitHub Actions) and observability with Prometheus/Grafana
* Cloud‑agnostic deployment—flip a single flag to run the same code on local Spark, Databricks, EMR, or Snowflake

---

## 🚀 Quick Start

```bash
# 1. Clone the repo
$ git clone https://github.com/<your‑org>/feathr‑movie‑streaming‑demo.git
$ cd feathr‑movie‑streaming‑demo

# 2. Launch the local sandbox (Spark + Redis + Prometheus)
$ docker compose up -d

# 3. Open the Feathr web console
$ open http://localhost:3000

# 4. Run the demo materialisation job
$ poetry run python src/materialise.py  # or `pip install -r requirements.txt` then `python ...`
```

> **Note** : the first run pulls Docker images (~1 GB) and builds Spark; subsequent runs are much faster.

---

## 🗂️ Repository Layout

```
.
├── data/                      # ✨ Sample parquet datasets (watch_events, users, movies)
├── src/                       # 🐍 Feature definitions & utility scripts
│   ├── features.py            #   – Declarative feature specs
│   ├── materialise.py         #   – Offline & online materialisation entry‑point
│   └── __init__.py
├── configs/
│   └── feathr_config.yaml     # ⚙️  Infra config (swap clusters/stores here)
├── docker-compose.yaml        # 🐳 Local Spark, Redis, Prometheus, Grafana
├── notebooks/
│   └── churn_feature_demo.ipynb # 📓 Interactive walkthrough
├── .github/workflows/ci.yml   # 🤖 Lint + unit tests on every PR
├── requirements.txt
├── pyproject.toml             # (optional) Poetry config
├── docs/
│   └── feathr_demo_architecture.png
└── README.md
```

---

# 📄 File Contents

Below are the complete source files so you can copy‑paste or scaffold your own repo quickly.

---

## `src/features.py`
```python
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
```

---

## `src/materialise.py`
```python
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
```

---

## `configs/feathr_config.yaml`
```yaml
project: movie_streaming_demo
spark_cluster: local[*]            # or "databricks", "emr", "snowflake"

offline_store:
  type: parquet
  location: data/feathr_offline

online_store:
  type: redis
  host: redis
  port: 6379

registry:
  type: file
  path: .feathr/registry.db
```

---

## `docker-compose.yaml`
```yaml
version: "3.9"
services:
  spark:
    image: bitnami/spark:3.4.1
    environment:
      - SPARK_MODE=master
      - SPARK_RPC_AUTHENTICATION_ENABLED=no
    ports:
      - "7077:7077"   # Spark master
      - "8080:8080"   # Spark UI
    volumes:
      - ./:/workspace

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  prometheus:
    image: prom/prometheus:v2.49.1
    ports:
      - "9090:9090"
    volumes:
      - ./configs/prometheus.yml:/etc/prometheus/prometheus.yml:ro

  grafana:
    image: grafana/grafana:10.2.3
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    depends_on:
      - prometheus

  feathr-ui:
    image: linkedin/feathr-ui:latest
    ports:
      - "3000:3000"
    environment:
      - FEATHR_BACKEND_URL=http://localhost:8080
```

---

## `requirements.txt`
```
feathr>=0.9.0
pyspark>=3.4.0
redis>=5.0.0
prometheus-client>=0.18.0
black>=23.10.0
pytest>=7.4.0
```
---

## 🖨️ Sample Output

Below is a **sample (fake) console transcript** from the first run of `python src/materialise.py` in the Docker sandbox. Feel free to include it in docs so newcomers know what to expect.

```text
$ poetry run python src/materialise.py
[2025‑04‑07 14:20:12]  INFO  feathr.client: Using config configs/feathr_config.yaml
[2025‑04‑07 14:20:12]  INFO  feathr.client: Registering 2 feature anchors and 2 features…
[2025‑04‑07 14:20:12]  INFO  feathr.registry: Wrote registry to .feathr/registry.db

────────────────────────────────────────  Spark Job 1/3  ────────────────────────────────────────
Stage 0: Parse feature plan                                     (  1  +   0  )   00:00 ✓
Stage 1: Scan data/watch_events.parquet                         ( 16  +   0  )   00:11 ✓
Stage 2: Aggregate watch_time_30d                               ( 16  +   0  )   01:43 ✓
Stage 3: Write Parquet offline sink                             (  1  +   0  )   00:08 ✓
──────────────────────────────────────────────────────────────────────────────────────────────────
[2025‑04‑07 14:22:15]  INFO  feathr.client: ✔︎ Offline materialisation finished (watch_time_30d)

────────────────────────────────────────  Spark Job 2/3  ────────────────────────────────────────
Stage 0: Scan data/users.parquet                               (  8  +   0  )   00:04 ✓
Stage 1: Compute lifetime_days                                 (  8  +   0  )   00:00 ✓
Stage 2: Write Parquet offline sink                            (  1  +   0  )   00:02 ✓
──────────────────────────────────────────────────────────────────────────────────────────────────
[2025‑04‑07 14:22:24]  INFO  feathr.client: ✔︎ Offline materialisation finished (lifetime_days)

────────────────────────────────────────  Spark Job 3/3  ────────────────────────────────────────
Stage 0: Stream features to Redis (hash key pattern: user_id:*) (  4  +   0  )   00:22 ✓
──────────────────────────────────────────────────────────────────────────────────────────────────
[2025‑04‑07 14:22:48]  INFO  feathr.client: ✔︎ Online materialisation finished (2 features, 4.2 M rows)

[2025‑04‑07 14:22:48]  INFO  feathr.client: Fetching point‑in‑time training dataset…
[2025‑04‑07 14:22:53]  INFO  feathr.client: Training dataset rows: 105 328

[2025‑04‑07 14:22:53]  INFO  feathr.client: Example online lookup for user_id=42
Online lookup: {'watch_time_30d': 17432.0, 'lifetime_days': 386}

Total wall‑clock time: 2 min 41 s
```

### Next Steps

* Drop your sample parquet files into `data/` (or mount an S3 bucket) and run `python src/materialise.py`.
* Explore feature lineage in the Feathr web console at `http://localhost:3000`.
* Open Grafana (`http://localhost:3001`, admin/admin) to view freshness & null‑rate dashboards.
* Swap `spark_cluster` to `databricks` and point `online_store` at a managed Redis to move to the cloud.









