#!/bin/bash

# Database Health Check Script
# Comprehensive health monitoring for all database services
# Usage: ./health_check.sh <environment> [--detailed]

set -e

ENVIRONMENT=${1:-dev}
DETAILED=${2}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Health status counters
HEALTHY_COUNT=0
UNHEALTHY_COUNT=0
WARNING_COUNT=0

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[HEALTHY]${NC} $1"
    HEALTHY_COUNT=$((HEALTHY_COUNT + 1))
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    WARNING_COUNT=$((WARNING_COUNT + 1))
}

log_error() {
    echo -e "${RED}[UNHEALTHY]${NC} $1"
    UNHEALTHY_COUNT=$((UNHEALTHY_COUNT + 1))
}

log_detail() {
    if [ "$DETAILED" = "--detailed" ]; then
        echo -e "${CYAN}[DETAIL]${NC} $1"
    fi
}

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    log_error "Invalid environment: $ENVIRONMENT"
    log_info "Supported environments: dev, staging, prod"
    exit 1
fi

# Header
echo -e "${PURPLE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║            DATABASE HEALTH CHECK - $(echo $ENVIRONMENT | tr '[:lower:]' '[:upper:]') ENVIRONMENT              ║${NC}"
echo -e "${PURPLE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

cd "$BASE_DIR"

# Container status check
check_container_status() {
    local service=$1
    local container_name="${service}_${ENVIRONMENT}"
    
    log_info "🔍 Checking $service container status..."
    
    # Check if container exists and is running
    if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$container_name"; then
        local status=$(docker ps --filter "name=$container_name" --format "{{.Status}}")
        if [[ "$status" == Up* ]]; then
            log_success "$service container is running"
            log_detail "Status: $status"
            return 0
        else
            log_error "$service container is not healthy"
            log_detail "Status: $status"
            return 1
        fi
    else
        log_error "$service container is not running or doesn't exist"
        return 1
    fi
}

# PostgreSQL health check
check_postgres_health() {
    local container_name="postgres_${ENVIRONMENT}"
    
    if ! check_container_status "postgres"; then
        return 1
    fi
    
    # Database-specific health checks
    case $ENVIRONMENT in
        dev) PG_USER="app_dev_user"; PG_DB="app_dev_db" ;;
        staging) PG_USER="app_staging_user"; PG_DB="app_staging_db" ;;
        prod) PG_USER="app_prod_user"; PG_DB="app_prod_db" ;;
    esac
    
    # Connection test
    if docker exec "$container_name" pg_isready -U "$PG_USER" -d "$PG_DB" > /dev/null 2>&1; then
        log_success "PostgreSQL is accepting connections"
    else
        log_error "PostgreSQL is not accepting connections"
        return 1
    fi
    
    if [ "$DETAILED" = "--detailed" ]; then
        # Get additional metrics
        local connections=$(docker exec "$container_name" psql -U "$PG_USER" -d "$PG_DB" -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs || echo "N/A")
        local db_size=$(docker exec "$container_name" psql -U "$PG_USER" -d "$PG_DB" -t -c "SELECT pg_size_pretty(pg_database_size('$PG_DB'));" 2>/dev/null | xargs || echo "N/A")
        
        log_detail "Active connections: $connections"
        log_detail "Database size: $db_size"
    fi
    
    return 0
}

# Redis health check
check_redis_health() {
    local container_name="redis_${ENVIRONMENT}"
    
    if ! check_container_status "redis"; then
        return 1
    fi
    
    # Redis ping test
    if docker exec "$container_name" redis-cli ping 2>/dev/null | grep -q "PONG"; then
        log_success "Redis is responding to ping"
    else
        log_error "Redis is not responding to ping"
        return 1
    fi
    
    if [ "$DETAILED" = "--detailed" ]; then
        # Get Redis info
        local memory_usage=$(docker exec "$container_name" redis-cli info memory 2>/dev/null | grep "used_memory_human" | cut -d: -f2 | tr -d '\r' || echo "N/A")
        local connected_clients=$(docker exec "$container_name" redis-cli info clients 2>/dev/null | grep "connected_clients" | cut -d: -f2 | tr -d '\r' || echo "N/A")
        
        log_detail "Memory usage: $memory_usage"
        log_detail "Connected clients: $connected_clients"
    fi
    
    return 0
}

# Neo4j health check
check_neo4j_health() {
    local container_name="neo4j_${ENVIRONMENT}"
    
    if ! check_container_status "neo4j"; then
        return 1
    fi
    
    # Neo4j connectivity test
    if docker exec "$container_name" cypher-shell -u neo4j -p "\$(cat /run/secrets/neo4j_auth | cut -d/ -f2)" "RETURN 1;" > /dev/null 2>&1; then
        log_success "Neo4j is accepting queries"
    else
        log_error "Neo4j is not accepting queries"
        return 1
    fi
    
    if [ "$DETAILED" = "--detailed" ]; then
        # Get Neo4j metrics
        local node_count=$(docker exec "$container_name" cypher-shell -u neo4j -p "\$(cat /run/secrets/neo4j_auth | cut -d/ -f2)" "MATCH (n) RETURN count(n);" 2>/dev/null | tail -n +2 | head -n 1 || echo "N/A")
        local relationship_count=$(docker exec "$container_name" cypher-shell -u neo4j -p "\$(cat /run/secrets/neo4j_auth | cut -d/ -f2)" "MATCH ()-[r]->() RETURN count(r);" 2>/dev/null | tail -n +2 | head -n 1 || echo "N/A")
        
        log_detail "Node count: $node_count"
        log_detail "Relationship count: $relationship_count"
    fi
    
    return 0
}

# Qdrant health check
check_qdrant_health() {
    local container_name="qdrant_${ENVIRONMENT}"
    
    if ! check_container_status "qdrant"; then
        return 1
    fi
    
    # Qdrant health endpoint test
    if docker exec "$container_name" curl -s http://localhost:6333/health | grep -q "ok"; then
        log_success "Qdrant health endpoint is responding"
    else
        log_error "Qdrant health endpoint is not responding"
        return 1
    fi
    
    if [ "$DETAILED" = "--detailed" ]; then
        # Get collections info
        local collections=$(docker exec "$container_name" curl -s http://localhost:6333/collections 2>/dev/null | jq -r '.result.collections[]?.name' 2>/dev/null | wc -l || echo "N/A")
        
        log_detail "Collection count: $collections"
    fi
    
    return 0
}

# MinIO health check
check_minio_health() {
    local container_name="minio_${ENVIRONMENT}"
    
    if ! check_container_status "minio"; then
        return 1
    fi
    
    # MinIO health endpoint test
    if docker exec "$container_name" curl -f http://localhost:9000/minio/health/live > /dev/null 2>&1; then
        log_success "MinIO health endpoint is responding"
    else
        log_error "MinIO health endpoint is not responding"
        return 1
    fi
    
    if [ "$DETAILED" = "--detailed" ]; then
        # Get storage info
        local disk_usage=$(docker exec "$container_name" df -h /data 2>/dev/null | tail -1 | awk '{print $3 "/" $2 " (" $5 ")"}' || echo "N/A")
        
        log_detail "Disk usage: $disk_usage"
    fi
    
    return 0
}

# Network connectivity check
check_network_connectivity() {
    log_info "🌐 Checking network connectivity between services..."
    
    local network_name="app_db_network_${ENVIRONMENT}"
    
    # Check if network exists
    if docker network ls | grep -q "$network_name"; then
        log_success "Database network exists and is accessible"
        
        if [ "$DETAILED" = "--detailed" ]; then
            local containers=$(docker network inspect "$network_name" --format '{{range .Containers}}{{.Name}} {{end}}' 2>/dev/null || echo "")
            log_detail "Connected containers: $containers"
        fi
    else
        log_error "Database network is missing"
        return 1
    fi
}

# Volume health check
check_volume_health() {
    log_info "💾 Checking volume health..."
    
    local volumes=("pgdata_${ENVIRONMENT}" "redisdata_${ENVIRONMENT}" "neo4jdata_${ENVIRONMENT}" "qdrantdata_${ENVIRONMENT}" "minio_data_${ENVIRONMENT}")
    local healthy_volumes=0
    
    for volume in "${volumes[@]}"; do
        if docker volume ls | grep -q "$volume"; then
            healthy_volumes=$((healthy_volumes + 1))
            if [ "$DETAILED" = "--detailed" ]; then
                local size=$(docker system df -v 2>/dev/null | grep "$volume" | awk '{print $3}' || echo "N/A")
                log_detail "Volume $volume: $size"
            fi
        else
            log_warning "Volume $volume is missing"
        fi
    done
    
    if [ $healthy_volumes -eq ${#volumes[@]} ]; then
        log_success "All volumes are healthy ($healthy_volumes/${#volumes[@]})"
    else
        log_warning "Some volumes are missing ($healthy_volumes/${#volumes[@]})"
    fi
}

# Resource usage check
check_resource_usage() {
    if [ "$DETAILED" = "--detailed" ]; then
        log_info "📊 Checking resource usage..."
        
        # Docker system info
        local docker_space=$(docker system df --format "table {{.Type}}\t{{.Size}}" 2>/dev/null || echo "Docker info unavailable")
        log_detail "Docker space usage:"
        echo "$docker_space" | while read -r line; do
            log_detail "  $line"
        done
        
        # Container resource usage
        log_detail "Container resource usage:"
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null | grep "_${ENVIRONMENT}" | while read -r line; do
            log_detail "  $line"
        done || log_detail "  Unable to get container stats"
    fi
}

# Main health check execution
echo "⏰ Health check started at: $(date)"
echo ""

# Check all services
services=("postgres" "redis" "neo4j" "qdrant" "minio")

for service in "${services[@]}"; do
    echo "----------------------------------------"
    case $service in
        postgres) check_postgres_health ;;
        redis) check_redis_health ;;
        neo4j) check_neo4j_health ;;
        qdrant) check_qdrant_health ;;
        minio) check_minio_health ;;
    esac
    echo ""
done

# Check network and volumes
check_network_connectivity
echo ""
check_volume_health
echo ""

# Check resource usage if detailed
check_resource_usage

# Summary
echo "========================================="
echo -e "${PURPLE}HEALTH CHECK SUMMARY${NC}"
echo "========================================="
echo -e "Environment: ${CYAN}$ENVIRONMENT${NC}"
echo -e "Timestamp: ${CYAN}$(date)${NC}"
echo ""
echo -e "🟢 Healthy services: ${GREEN}$HEALTHY_COUNT${NC}"
echo -e "🟡 Services with warnings: ${YELLOW}$WARNING_COUNT${NC}" 
echo -e "🔴 Unhealthy services: ${RED}$UNHEALTHY_COUNT${NC}"
echo ""

# Overall status
TOTAL_SERVICES=5
if [ $UNHEALTHY_COUNT -eq 0 ] && [ $HEALTHY_COUNT -eq $TOTAL_SERVICES ]; then
    echo -e "Overall Status: ${GREEN}✅ ALL SYSTEMS HEALTHY${NC}"
    exit 0
elif [ $UNHEALTHY_COUNT -eq 0 ] && [ $WARNING_COUNT -gt 0 ]; then
    echo -e "Overall Status: ${YELLOW}⚠️  MINOR ISSUES DETECTED${NC}"
    exit 0
else
    echo -e "Overall Status: ${RED}❌ CRITICAL ISSUES DETECTED${NC}"
    echo ""
    log_error "Some services are unhealthy. Please investigate immediately."
    exit 1
fi
