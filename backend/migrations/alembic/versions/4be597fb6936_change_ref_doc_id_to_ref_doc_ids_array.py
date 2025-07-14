"""change_ref_doc_id_to_ref_doc_ids_array

Revision ID: 4be597fb6936
Revises: 1d6ff6bfce68
Create Date: 2025-07-14 11:26:11.487267

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import json


# revision identifiers, used by Alembic.
revision: str = '4be597fb6936'
down_revision: Union[str, None] = '1d6ff6bfce68'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema to change ref_doc_id from single string to ref_doc_ids JSON array.
    
    This fixes the issue where multiple LlamaIndex documents from one file
    created multiple KnowledgeFile records.
    """
    
    # Step 1: Add the new ref_doc_ids column
    print("Adding ref_doc_ids JSON column...")
    op.add_column('knowledge_files', sa.Column('ref_doc_ids', sa.JSON(), nullable=True))
    
    # Step 2: Migrate existing data from ref_doc_id to ref_doc_ids
    print("Migrating existing ref_doc_id data to ref_doc_ids arrays...")
    
    # Get connection for data migration
    connection = op.get_bind()
    
    # First, identify files that have the same file_path (same S3 file) but different ref_doc_ids
    print("Identifying files with same file_path...")
    
    # Get all knowledge files with their ref_doc_ids
    result = connection.execute(
        sa.text("SELECT id, file_path, ref_doc_id FROM knowledge_files WHERE ref_doc_id IS NOT NULL ORDER BY file_path, created_at")
    )
    
    # Group by file_path and collect ref_doc_ids
    file_groups = {}
    for row in result:
        file_path = row.file_path
        ref_doc_id = row.ref_doc_id
        
        if file_path not in file_groups:
            file_groups[file_path] = {'records': [], 'ref_doc_ids': []}
        
        file_groups[file_path]['records'].append(row.id)
        file_groups[file_path]['ref_doc_ids'].append(ref_doc_id)
    
    # Process each file group
    for file_path, group in file_groups.items():
        records = group['records']
        ref_doc_ids = group['ref_doc_ids']
        
        if len(records) == 1:
            # Single record: convert ref_doc_id to single-item array
            print(f"Converting single ref_doc_id to array for file: {file_path}")
            connection.execute(
                sa.text("UPDATE knowledge_files SET ref_doc_ids = :ref_doc_ids WHERE id = :id"),
                {"ref_doc_ids": json.dumps(ref_doc_ids), "id": records[0]}
            )
        else:
            # Multiple records: consolidate into first record, delete others
            print(f"Consolidating {len(records)} records into one for file: {file_path}")
            
            # Update first record with all ref_doc_ids
            primary_record = records[0]
            connection.execute(
                sa.text("UPDATE knowledge_files SET ref_doc_ids = :ref_doc_ids WHERE id = :id"),
                {"ref_doc_ids": json.dumps(ref_doc_ids), "id": primary_record}
            )
            
            # Delete duplicate records
            for duplicate_id in records[1:]:
                connection.execute(
                    sa.text("DELETE FROM knowledge_files WHERE id = :id"),
                    {"id": duplicate_id}
                )
    
    print(f"Processed {len(file_groups)} unique files")
    
    # Step 3: Drop old indexes and column
    print("Dropping old ref_doc_id indexes...")
    try:
        op.drop_index(op.f('ix_knowledge_files_ref_doc'), table_name='knowledge_files')
    except Exception as e:
        print(f"Warning: Could not drop ix_knowledge_files_ref_doc: {e}")
    
    try:
        op.drop_index(op.f('ix_knowledge_files_ref_doc_id'), table_name='knowledge_files')
    except Exception as e:
        print(f"Warning: Could not drop ix_knowledge_files_ref_doc_id: {e}")
    
    print("Dropping ref_doc_id column...")
    op.drop_column('knowledge_files', 'ref_doc_id')
    
    # Step 4: Create new indexes
    print("Creating new file_path index...")
    op.create_index('ix_knowledge_files_file_path', 'knowledge_files', ['file_path'], unique=False)
    
    # Step 5: Fix vector collections scope index (from autogenerate)
    try:
        op.drop_index(op.f('ix_vector_collections_scope'), table_name='vector_collections')
    except Exception as e:
        print(f"Warning: Could not drop vector_collections scope index: {e}")
    
    op.create_index('ix_vector_collections_scope', 'vector_collections', ['scope', 'scope_id'], unique=False)
    
    print("Migration completed successfully!")
    print("📋 Summary:")
    print("   • Changed ref_doc_id (String) → ref_doc_ids (JSON array)")
    print("   • Consolidated duplicate KnowledgeFile records for same file")
    print("   • Updated indexes for better performance")
    print("   • 1 uploaded file now = 1 KnowledgeFile record")


def downgrade() -> None:
    """
    Downgrade schema back to ref_doc_id single string.
    
    WARNING: This will recreate multiple KnowledgeFile records for files
    that had multiple ref_doc_ids, potentially causing data issues.
    """
    
    print("WARNING: Downgrading will split consolidated records back into multiple records!")
    
    # Step 1: Fix vector collections scope index
    try:
        op.drop_index('ix_vector_collections_scope', table_name='vector_collections')
    except Exception as e:
        print(f"Warning: Could not drop vector_collections scope index: {e}")
    
    op.create_index(op.f('ix_vector_collections_scope'), 'vector_collections', ['scope'], unique=False)
    
    # Step 2: Add back ref_doc_id column
    print("Adding back ref_doc_id column...")
    op.add_column('knowledge_files', sa.Column('ref_doc_id', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    
    # Step 3: Migrate data back from ref_doc_ids to ref_doc_id
    print("Migrating ref_doc_ids arrays back to ref_doc_id...")
    
    connection = op.get_bind()
    
    # Get all records with ref_doc_ids
    result = connection.execute(
        sa.text("SELECT id, file_path, file_name, ref_doc_ids, user_id, collection_id, node_count, processing_status, indexed_in_vector_db, embeddings_generated, created_at FROM knowledge_files WHERE ref_doc_ids IS NOT NULL")
    )
    
    records_to_create = []
    records_to_update = []
    
    for row in result:
        try:
            ref_doc_ids = json.loads(row.ref_doc_ids) if isinstance(row.ref_doc_ids, str) else row.ref_doc_ids
            
            if ref_doc_ids and len(ref_doc_ids) > 0:
                # Update first record with first ref_doc_id
                records_to_update.append((row.id, ref_doc_ids[0]))
                
                # Create new records for additional ref_doc_ids
                for ref_doc_id in ref_doc_ids[1:]:
                    records_to_create.append({
                        'file_path': row.file_path,
                        'file_name': row.file_name,
                        'ref_doc_id': ref_doc_id,
                        'user_id': row.user_id,
                        'collection_id': row.collection_id,
                        'node_count': 0,  # Will need to be recalculated
                        'processing_status': row.processing_status,
                        'indexed_in_vector_db': row.indexed_in_vector_db,
                        'embeddings_generated': row.embeddings_generated
                    })
        except (json.JSONDecodeError, TypeError):
            # Skip malformed data
            continue
    
    # Update existing records
    for record_id, ref_doc_id in records_to_update:
        connection.execute(
            sa.text("UPDATE knowledge_files SET ref_doc_id = :ref_doc_id WHERE id = :id"),
            {"ref_doc_id": ref_doc_id, "id": record_id}
        )
    
    # Create new records
    for record_data in records_to_create:
        connection.execute(
            sa.text("""
                INSERT INTO knowledge_files (id, file_id, file_path, file_name, ref_doc_id, user_id, collection_id, node_count, processing_status, indexed_in_vector_db, embeddings_generated)
                VALUES (
                    'kf_' || substr(md5(random()::text), 1, 12),
                    'file_' || substr(md5(random()::text), 1, 8),
                    :file_path, :file_name, :ref_doc_id, :user_id, :collection_id, :node_count, :processing_status, :indexed_in_vector_db, :embeddings_generated
                )
            """),
            record_data
        )
    
    # Step 4: Drop new indexes and column
    print("Dropping new indexes...")
    try:
        op.drop_index('ix_knowledge_files_file_path', table_name='knowledge_files')
    except Exception as e:
        print(f"Warning: Could not drop file_path index: {e}")
    
    # Step 5: Recreate old indexes
    print("Recreating old ref_doc_id indexes...")
    op.create_index(op.f('ix_knowledge_files_ref_doc_id'), 'knowledge_files', ['ref_doc_id'], unique=True)
    op.create_index(op.f('ix_knowledge_files_ref_doc'), 'knowledge_files', ['ref_doc_id'], unique=False)
    
    # Step 6: Drop new column
    print("Dropping ref_doc_ids column...")
    op.drop_column('knowledge_files', 'ref_doc_ids')
    
    print("Downgrade completed - multiple records recreated for files with multiple ref_doc_ids")
