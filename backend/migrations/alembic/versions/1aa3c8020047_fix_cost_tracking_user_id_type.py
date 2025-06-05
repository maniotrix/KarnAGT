"""fix_cost_tracking_user_id_type

Revision ID: 1aa3c8020047
Revises: 4cb4872d7a59
Create Date: 2025-06-05 12:40:52.217755

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1aa3c8020047'
down_revision: Union[str, None] = '4cb4872d7a59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the existing foreign key constraint
    op.drop_constraint('cost_tracking_user_id_fkey', 'cost_tracking', type_='foreignkey')
    
    # Clear the cost_tracking table since we're changing the user_id type
    # This is safe for development but would need data migration in production
    op.execute("DELETE FROM cost_tracking")
    
    # Drop the existing user_id column
    op.drop_column('cost_tracking', 'user_id')
    
    # Add the new user_id column as INTEGER
    op.add_column('cost_tracking', sa.Column('user_id', sa.INTEGER(), nullable=False))
    
    # Recreate the foreign key constraint pointing to users.id
    op.create_foreign_key('cost_tracking_user_id_fkey', 'cost_tracking', 'users', ['user_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the foreign key constraint
    op.drop_constraint('cost_tracking_user_id_fkey', 'cost_tracking', type_='foreignkey')
    
    # Change the user_id column type back to VARCHAR
    op.alter_column('cost_tracking', 'user_id',
                   existing_type=sa.INTEGER(),
                   type_=sa.VARCHAR(length=36),
                   existing_nullable=False)
    
    # Recreate the original foreign key constraint pointing to users.user_id
    op.create_foreign_key('cost_tracking_user_id_fkey', 'cost_tracking', 'users', ['user_id'], ['user_id'])
