"""unify preparation model, remove postponed/priority/view_type/preparation_periods tables, add is_preparation/is_important fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-10 17:02:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === events 表修改 ===
    # 1. 删除 postponed 字段
    op.drop_column('events', 'postponed')
    
    # 2. 添加新字段
    op.add_column('events', sa.Column('is_preparation', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('events', sa.Column('parent_event_id', UUID(as_uuid=True), nullable=True))
    op.add_column('events', sa.Column('parent_task_id', UUID(as_uuid=True), nullable=True))
    
    # 3. 添加外键约束
    op.create_foreign_key('fk_events_parent_event_id', 'events', 'events', ['parent_event_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_events_parent_task_id', 'events', 'tasks', ['parent_task_id'], ['id'], ondelete='SET NULL')
    
    # 4. 添加 CHECK 约束（严格互斥）
    op.create_check_constraint(
        'ck_event_preparation_parent_mutex',
        'events',
        sa.text('(parent_event_id IS NULL OR parent_task_id IS NULL)')
    )

    # === tasks 表修改 ===
    # 1. 删除 priority 和 view_type
    op.drop_column('tasks', 'priority')
    op.drop_column('tasks', 'view_type')
    
    # 2. 添加 is_important 字段
    op.add_column('tasks', sa.Column('is_important', sa.Boolean(), server_default=sa.text('false'), nullable=False))

    # === 删除准备时段子表 ===
    op.drop_table('task_preparation_periods')
    op.drop_table('event_preparation_periods')


def downgrade() -> None:
    # === 恢复准备时段子表 ===
    op.create_table('event_preparation_periods',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('event_id', UUID(as_uuid=True), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table('task_preparation_periods',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('task_id', UUID(as_uuid=True), sa.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # === tasks 恢复 ===
    op.add_column('tasks', sa.Column('priority', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.add_column('tasks', sa.Column('view_type', sa.String(20), server_default=sa.text("'deadline'"), nullable=False))
    op.drop_column('tasks', 'is_important')

    # === events 恢复 ===
    op.drop_constraint('ck_event_preparation_parent_mutex', 'events', type_='check')
    op.drop_constraint('fk_events_parent_task_id', 'events', type_='foreignkey')
    op.drop_constraint('fk_events_parent_event_id', 'events', type_='foreignkey')
    op.drop_column('events', 'parent_task_id')
    op.drop_column('events', 'parent_event_id')
    op.drop_column('events', 'is_preparation')
    op.add_column('events', sa.Column('postponed', sa.Boolean(), server_default=sa.text('false'), nullable=False))