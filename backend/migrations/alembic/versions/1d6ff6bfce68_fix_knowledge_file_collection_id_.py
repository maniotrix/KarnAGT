"""fix_knowledge_file_collection_id_foreign_key

Revision ID: 1d6ff6bfce68
Revises: fcaf26b886b8
Create Date: 2025-07-07 18:34:35.085635

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1d6ff6bfce68'
down_revision: Union[str, None] = 'fcaf26b886b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to use proper foreign key from KnowledgeFile to VectorCollection."""
    
    # Step 1: Add temporary column for new foreign key relationship
    op.add_column('knowledge_files', 
                  sa.Column('vector_collection_id', sa.String(length=50), nullable=True))
    
    # Step 2: Migrate data from collection_name to collection.id
    # Update knowledge_files.vector_collection_id = vector_collections.id 
    # WHERE knowledge_files.collection_id = vector_collections.collection_name
    op.execute("""
        UPDATE knowledge_files 
        SET vector_collection_id = vc.id
        FROM vector_collections vc
        WHERE knowledge_files.collection_id = vc.collection_name
    """)
    
    # Step 3: Drop old indexes and column
    op.drop_index('ix_knowledge_files_collection_id', table_name='knowledge_files')
    op.drop_index('ix_knowledge_files_collection_status', table_name='knowledge_files')
    op.drop_column('knowledge_files', 'collection_id')
    
    # Step 4: Rename new column to collection_id
    op.alter_column('knowledge_files', 'vector_collection_id', 
                   new_column_name='collection_id')
    
    # Step 5: Create foreign key constraint
    op.create_foreign_key(
        'fk_knowledge_files_vector_collection',
        'knowledge_files', 'vector_collections',
        ['collection_id'], ['id']
    )
    
    # Step 6: Recreate indexes
    op.create_index('ix_knowledge_files_collection_id', 'knowledge_files', ['collection_id'])
    op.create_index('ix_knowledge_files_collection_status', 'knowledge_files', ['collection_id', 'indexed_in_vector_db'])


def downgrade() -> None:
    """Downgrade schema to use collection_name relationship."""
    
    # Step 1: Drop foreign key constraint
    op.drop_constraint('fk_knowledge_files_vector_collection', 'knowledge_files', type_='foreignkey')
    
    # Step 2: Drop indexes
    op.drop_index('ix_knowledge_files_collection_id', table_name='knowledge_files')
    op.drop_index('ix_knowledge_files_collection_status', table_name='knowledge_files')
    
    # Step 3: Add temporary column for old relationship
    op.add_column('knowledge_files', 
                  sa.Column('collection_name_ref', sa.String(length=100), nullable=True))
    
    # Step 4: Migrate data back from collection.id to collection_name
    op.execute("""
        UPDATE knowledge_files 
        SET collection_name_ref = vc.collection_name
        FROM vector_collections vc
        WHERE knowledge_files.collection_id = vc.id
    """)
    
    # Step 5: Drop new column
    op.drop_column('knowledge_files', 'collection_id')
    
    # Step 6: Rename old column back
    op.alter_column('knowledge_files', 'collection_name_ref', 
                   new_column_name='collection_id')
    
    # Step 7: Recreate old indexes
    op.create_index('ix_knowledge_files_collection_id', 'knowledge_files', ['collection_id'])
    op.create_index('ix_knowledge_files_collection_status', 'knowledge_files', ['collection_id', 'indexed_in_vector_db'])
