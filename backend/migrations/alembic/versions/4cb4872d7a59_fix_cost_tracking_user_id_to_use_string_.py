"""Fix cost_tracking user_id to use string foreign key

Revision ID: 4cb4872d7a59
Revises: 0c8c6f5381e8
Create Date: 2025-06-05 11:58:15.657893

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4cb4872d7a59'
down_revision: Union[str, None] = '0c8c6f5381e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Drop the existing foreign key constraint first
    op.drop_constraint('cost_tracking_user_id_fkey', 'cost_tracking', type_='foreignkey')
    
    # Step 2: Now we can safely change the column type
    op.alter_column('cost_tracking', 'user_id',
               existing_type=sa.INTEGER(),
               type_=sa.String(length=36),
               existing_nullable=False)
    
    # Step 3: Create the new foreign key constraint to users.user_id
    op.create_foreign_key('cost_tracking_user_id_fkey', 'cost_tracking', 'users', ['user_id'], ['user_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Step 1: Drop the new foreign key constraint
    op.drop_constraint('cost_tracking_user_id_fkey', 'cost_tracking', type_='foreignkey')
    
    # Step 2: Change column type back to integer
    op.alter_column('cost_tracking', 'user_id',
               existing_type=sa.String(length=36),
               type_=sa.INTEGER(),
               existing_nullable=False)
    
    # Step 3: Recreate the old foreign key constraint to users.id
    op.create_foreign_key('cost_tracking_user_id_fkey', 'cost_tracking', 'users', ['user_id'], ['id'])
