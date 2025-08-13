#!/bin/bash

# Database Backup Script
# Automated backup for all database services
# Usage: ./backup.sh <environment> [service]

set -e

ENVIRONMENT=${1:-dev}
SERVICE=${2:-all}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${BASE_DIR}/backups/${ENVIRONMENT}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

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

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    log_error "Invalid environment: $ENVIRONMENT"
    log_info "Supported environments: dev, staging, prod"
    exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

log_info "🚀 Starting backup for $ENVIRONMENT environment"
log_info "📁 Backup directory: $BACKUP_DIR"
log_info "⏰ Timestamp: $TIMESTAMP"

# Use Python db_manager for backup
cd "$BASE_DIR"

if [ "$SERVICE" = "all" ]; then
    log_info "💾 Creating comprehensive backup for all services..."
    if python db_manager.py backup --env="$ENVIRONMENT"; then
        log_success "✅ All services backed up successfully"
        
        # Create backup manifest
        MANIFEST_FILE="${BACKUP_DIR}/backup_manifest_${TIMESTAMP}.txt"
        {
            echo "Backup Manifest"
            echo "==============="
            echo "Environment: $ENVIRONMENT"
            echo "Timestamp: $TIMESTAMP"
            echo "Date: $(date)"
            echo ""
            echo "Backup Files:"
            find "$BACKUP_DIR" -name "*${TIMESTAMP}*" -type f | sort
            echo ""
            echo "Total Size:"
            du -sh "$BACKUP_DIR" | cut -f1
        } > "$MANIFEST_FILE"
        
        log_success "📋 Backup manifest created: $MANIFEST_FILE"
    else
        log_error "❌ Backup failed"
        exit 1
    fi
else
    log_info "💾 Creating backup for service: $SERVICE"
    if python db_manager.py backup --env="$ENVIRONMENT" --service="$SERVICE"; then
        log_success "✅ Service $SERVICE backed up successfully"
    else
        log_error "❌ Backup failed for service: $SERVICE"
        exit 1
    fi
fi

# Cleanup old backups (keep last 10)
log_info "🧹 Cleaning up old backups..."
cd "$BACKUP_DIR"
ls -t *backup* 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
log_success "✅ Cleanup completed"

log_success "🎉 Backup operation completed successfully"
