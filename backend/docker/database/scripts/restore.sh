#!/bin/bash

# Database Restore Script
# Restore database services from backup
# Usage: ./restore.sh <environment> <backup_timestamp> [service]

set -e

ENVIRONMENT=${1}
BACKUP_TIMESTAMP=${2}
SERVICE=${3:-all}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${BASE_DIR}/backups/${ENVIRONMENT}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate parameters
if [ -z "$ENVIRONMENT" ] || [ -z "$BACKUP_TIMESTAMP" ]; then
    log_error "Usage: $0 <environment> <backup_timestamp> [service]"
    log_info "Example: $0 dev 20240101_120000"
    log_info "         $0 dev 20240101_120000 postgres"
    exit 1
fi

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    log_error "Invalid environment: $ENVIRONMENT"
    log_info "Supported environments: dev, staging, prod"
    exit 1
fi

# Check if backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    log_error "Backup directory does not exist: $BACKUP_DIR"
    exit 1
fi

log_warning "⚠️  DESTRUCTIVE OPERATION WARNING ⚠️"
log_warning "This will restore database(s) from backup, potentially overwriting current data."
log_info "Environment: $ENVIRONMENT"
log_info "Backup timestamp: $BACKUP_TIMESTAMP"
log_info "Service: $SERVICE"
log_info "Backup directory: $BACKUP_DIR"

# Safety prompt (except in CI/automated environments)
if [ -z "$CI" ] && [ -z "$AUTOMATED_RESTORE" ]; then
    echo -n "Are you sure you want to continue? (yes/no): "
    read -r response
    if [ "$response" != "yes" ]; then
        log_info "Restore cancelled by user"
        exit 0
    fi
fi

cd "$BASE_DIR"

# Restore function for PostgreSQL
restore_postgres() {
    log_info "🐘 Restoring PostgreSQL..."
    
    local container_name="postgres_${ENVIRONMENT}"
    local backup_file="${BACKUP_DIR}/postgres_backup_${BACKUP_TIMESTAMP}.dump"
    
    if [ ! -f "$backup_file" ]; then
        backup_file="${BACKUP_DIR}/postgres_backup_${BACKUP_TIMESTAMP}.sql"
    fi
    
    if [ ! -f "$backup_file" ]; then
        log_error "PostgreSQL backup file not found for timestamp: $BACKUP_TIMESTAMP"
        return 1
    fi
    
    # Environment-specific database config
    case $ENVIRONMENT in
        dev)
            PG_USER="app_dev_user"
            PG_DB="app_dev_db"
            ;;
        staging)
            PG_USER="app_staging_user"
            PG_DB="app_staging_db"
            ;;
        prod)
            PG_USER="app_prod_user"
            PG_DB="app_prod_db"
            ;;
    esac
    
    # Copy backup file to container
    docker cp "$backup_file" "${container_name}:/tmp/restore_backup"
    
    # Restore based on file type
    if [[ "$backup_file" == *.dump ]]; then
        # Custom format restore
        docker exec -e "PGPASSWORD=\$(cat /run/secrets/postgres_password)" \
            "$container_name" pg_restore -U "$PG_USER" -d "$PG_DB" --clean --if-exists /tmp/restore_backup
    else
        # SQL format restore
        docker exec -e "PGPASSWORD=\$(cat /run/secrets/postgres_password)" \
            "$container_name" psql -U "$PG_USER" -d "$PG_DB" -f /tmp/restore_backup
    fi
    
    if [ $? -eq 0 ]; then
        log_success "✅ PostgreSQL restored successfully"
        return 0
    else
        log_error "❌ PostgreSQL restore failed"
        return 1
    fi
}

# Restore function for Redis
restore_redis() {
    log_info "🔴 Restoring Redis..."
    
    local container_name="redis_${ENVIRONMENT}"
    local backup_file="${BACKUP_DIR}/redis_backup_${BACKUP_TIMESTAMP}.rdb"
    
    if [ ! -f "$backup_file" ]; then
        log_error "Redis backup file not found for timestamp: $BACKUP_TIMESTAMP"
        return 1
    fi
    
    # Stop Redis temporarily
    docker exec "$container_name" redis-cli --pass "\$(cat /run/secrets/redis_password)" SHUTDOWN NOSAVE || true
    
    # Copy backup file
    docker cp "$backup_file" "${container_name}:/data/dump.rdb"
    
    # Restart Redis container
    docker restart "$container_name"
    
    log_success "✅ Redis restored successfully"
    return 0
}

# Restore function for Neo4j
restore_neo4j() {
    log_info "🔵 Restoring Neo4j..."
    
    local container_name="neo4j_${ENVIRONMENT}"
    local backup_file="${BACKUP_DIR}/neo4j_backup_${BACKUP_TIMESTAMP}.dump"
    local db_name="app_${ENVIRONMENT}_graph"
    
    if [ ! -f "$backup_file" ]; then
        log_error "Neo4j backup file not found for timestamp: $BACKUP_TIMESTAMP"
        return 1
    fi
    
    # Stop Neo4j
    docker stop "$container_name"
    
    # Copy backup file to container
    docker cp "$backup_file" "${container_name}:/tmp/restore.dump"
    
    # Start container
    docker start "$container_name"
    
    # Wait for Neo4j to start
    sleep 10
    
    # Load the dump
    docker exec "$container_name" neo4j-admin database load --from-path=/tmp --database="$db_name" --overwrite-destination=true
    
    # Restart to apply changes
    docker restart "$container_name"
    
    log_success "✅ Neo4j restored successfully"
    return 0
}

# Restore function for Qdrant
restore_qdrant() {
    log_info "🟡 Restoring Qdrant..."
    
    local container_name="qdrant_${ENVIRONMENT}"
    local backup_file="${BACKUP_DIR}/qdrant_backup_${BACKUP_TIMESTAMP}.tar.gz"
    
    if [ ! -f "$backup_file" ]; then
        log_error "Qdrant backup file not found for timestamp: $BACKUP_TIMESTAMP"
        return 1
    fi
    
    # Stop Qdrant
    docker stop "$container_name"
    
    # Copy and extract backup
    docker cp "$backup_file" "${container_name}:/tmp/qdrant_restore.tar.gz"
    docker start "$container_name"
    sleep 5
    docker exec "$container_name" tar -xzf /tmp/qdrant_restore.tar.gz -C /qdrant/
    
    # Restart container
    docker restart "$container_name"
    
    log_success "✅ Qdrant restored successfully"
    return 0
}

# Restore function for MinIO
restore_minio() {
    log_info "🟠 Restoring MinIO..."
    
    local container_name="minio_${ENVIRONMENT}"
    local backup_file="${BACKUP_DIR}/minio_backup_${BACKUP_TIMESTAMP}.tar.gz"
    
    if [ ! -f "$backup_file" ]; then
        log_error "MinIO backup file not found for timestamp: $BACKUP_TIMESTAMP"
        return 1
    fi
    
    # Stop MinIO
    docker stop "$container_name"
    
    # Copy and extract backup
    docker cp "$backup_file" "${container_name}:/tmp/minio_restore.tar.gz"
    docker start "$container_name"
    sleep 5
    docker exec "$container_name" tar -xzf /tmp/minio_restore.tar.gz -C /data/
    
    # Restart container
    docker restart "$container_name"
    
    log_success "✅ MinIO restored successfully"
    return 0
}

# Main restore logic
log_info "🚀 Starting restore operation..."

success_count=0
total_count=0

if [ "$SERVICE" = "all" ]; then
    services=("postgres" "redis" "neo4j" "qdrant" "minio")
else
    services=("$SERVICE")
fi

for svc in "${services[@]}"; do
    total_count=$((total_count + 1))
    case $svc in
        postgres)
            if restore_postgres; then
                success_count=$((success_count + 1))
            fi
            ;;
        redis)
            if restore_redis; then
                success_count=$((success_count + 1))
            fi
            ;;
        neo4j)
            if restore_neo4j; then
                success_count=$((success_count + 1))
            fi
            ;;
        qdrant)
            if restore_qdrant; then
                success_count=$((success_count + 1))
            fi
            ;;
        minio)
            if restore_minio; then
                success_count=$((success_count + 1))
            fi
            ;;
        *)
            log_error "Unknown service: $svc"
            ;;
    esac
done

# Summary
log_info "📊 Restore Summary:"
log_info "   Services processed: $total_count"
log_info "   Successful restores: $success_count"
log_info "   Failed restores: $((total_count - success_count))"

if [ "$success_count" -eq "$total_count" ]; then
    log_success "🎉 All restore operations completed successfully"
    
    # Run health check
    log_info "🩺 Running health check..."
    if python db_manager.py health --env="$ENVIRONMENT"; then
        log_success "✅ Health check passed"
    else
        log_warning "⚠️  Health check failed - please investigate"
    fi
    
    exit 0
else
    log_error "❌ Some restore operations failed"
    exit 1
fi
