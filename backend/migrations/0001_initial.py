"""Initial schema snapshot (SQLite/Postgres compatible).

Production deployments should run Alembic; this file documents the MVP schema
created by Base.metadata.create_all(). See docs/DEVELOPMENT.md.
"""
revision = "0001_initial"
down_revision = None

TABLES = ["users", "projects", "video_assets", "detected_objects",
          "segmentation_masks", "editing_jobs", "editing_operations"]
