"""数据库迁移脚本，供 deploy.bat 调用"""
from sqlalchemy import create_engine, inspect, text

engine = create_engine("postgresql://postgres:postgres@postgres:5432/time_manager")
insp = inspect(engine)

# 检查是否需要迁移
events_cols = {c["name"] for c in insp.get_columns("events")}
tasks_cols = {c["name"] for c in insp.get_columns("tasks")}

needs_migration = False

# events：需要 is_preparation 而不是 postponed
if "postponed" in events_cols:
    needs_migration = True

# tasks：需要 is_important 而不是 priority
if "priority" in tasks_cols:
    needs_migration = True

if not needs_migration:
    print("数据库已是最新，无需迁移")
    exit(0)

print("检测到旧 schema，开始迁移...")
with engine.connect() as conn:
    trans = conn.begin()
    try:
        if "postponed" in events_cols:
            conn.execute(text("ALTER TABLE events DROP COLUMN IF EXISTS postponed"))
        if "is_preparation" not in events_cols:
            conn.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS is_preparation BOOLEAN NOT NULL DEFAULT false"))
        if "parent_event_id" not in events_cols:
            conn.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS parent_event_id UUID"))
        if "parent_task_id" not in events_cols:
            conn.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS parent_task_id UUID"))
        if "priority" in tasks_cols:
            conn.execute(text("ALTER TABLE tasks DROP COLUMN IF EXISTS priority"))
        if "view_type" in tasks_cols:
            conn.execute(text("ALTER TABLE tasks DROP COLUMN IF EXISTS view_type"))
        if "is_important" not in tasks_cols:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS is_important BOOLEAN NOT NULL DEFAULT false"))

        # 检查并删除旧表
        tables = insp.get_table_names()
        if "event_preparation_periods" in tables:
            conn.execute(text("DROP TABLE IF EXISTS event_preparation_periods CASCADE"))
        if "task_preparation_periods" in tables:
            conn.execute(text("DROP TABLE IF EXISTS task_preparation_periods CASCADE"))

        trans.commit()
        print("✅ 迁移完成！")
    except Exception as e:
        trans.rollback()
        print(f"❌ 迁移失败: {e}")
        exit(1)