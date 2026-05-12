# ChatGPT Clone Backend

Advanced ChatGPT Clone with Memory Management, Knowledge Integration, and Cost Optimization.

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- OpenAI API Key

### 2. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Create environment file
cp env.example .env

# Edit .env file and add your API keys
# Minimum required: OPENAI_API_KEY
```

### 3. Configuration

Edit `.env` file with your settings:

```env
# Required
OPENAI_API_KEY=your-openai-api-key-here

# Database (setup required)
DATABASE_URL=postgresql://user:password@localhost:5432/chatgpt_clone
REDIS_URL=redis://localhost:6379/0

# Optional (for advanced features)
QDRANT_URL=http://localhost:6333
NEO4J_URL=bolt://localhost:7687
```

### 4. Run Development Server

```bash
# Method 1: Using the startup script
python start_dev.py

# Method 2: Using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Method 3: Using Python module
python -m app.main
```

## 📁 Project Structure

```
backend/
├── app/                    # Main application package
│   ├── api/               # API routes and endpoints
│   │   └── v1/           # API version 1
│   │       └── endpoints/ # Individual endpoint modules
│   ├── core/             # Core application components
│   ├── services/         # Business logic services
│   │   ├── chat/         # Chat processing
│   │   ├── memory/       # Memory management
│   │   ├── search/       # Hybrid search
│   │   ├── knowledge/    # Knowledge base
│   │   ├── cost/         # Cost tracking
│   │   └── tools/        # Tool execution
│   ├── models/           # Data models
│   ├── workers/          # Background tasks
│   ├── integrations/     # External service integrations
│   └── utils/           # Utility functions
├── aicore/              # Existing agent code
├── migrations/          # Database migrations
├── tests/              # Test suites
├── scripts/            # Setup and deployment scripts
└── docker/             # Container configuration
```

## 🛠️ Development Features

### Current Status
✅ **Completed:**
- FastAPI application structure
- Configuration management
- API routing setup
- Database connection setup
- Environment configuration

🚧 **In Progress:**
- Chat endpoints implementation
- Memory management system
- File processing pipeline
- Authentication system

📋 **Planned:**
- Advanced memory with Graphiti
- Vector search with Qdrant
- Cost tracking and analytics
- Background processing with Celery

### API Endpoints

Once fully implemented, the API will include:

```
/api/v1/
├── auth/          # Authentication
├── chat/          # Chat conversations
├── memory/        # Memory management
├── files/         # File upload/processing
├── tools/         # Tool execution
└── analytics/     # Usage analytics
```

## 🔧 Configuration Options

### Core Settings
- `PROJECT_NAME`: Application name
- `ENVIRONMENT`: development/staging/production
- `DEBUG`: Enable debug mode
- `SECRET_KEY`: JWT signing key (change in production!)

### AI Services
- `OPENAI_API_KEY`: OpenAI API key (required)
- `OPENAI_MODEL`: Model to use (default: gpt-4o-mini)
- `OPENAI_TEMPERATURE`: Response creativity (0.0-1.0)

### Memory Management
- `MEMORY_IMPORTANCE_THRESHOLD`: Minimum importance to store
- `MEMORY_DECAY_RATE`: How fast memories fade
- `MEMORY_MAX_AGE_DAYS`: Maximum memory retention

### Cost Management
- `COST_TRACKING_ENABLED`: Enable cost tracking
- `DEFAULT_USER_QUOTA_USD`: Default user spending limit
- `COST_ALERT_THRESHOLD`: Alert when % of quota used

## 🐳 Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Production deployment
docker-compose -f docker-compose.prod.yml up
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test category
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

## 📊 Monitoring

- **Health Check**: `GET /health`
- **API Docs**: `GET /docs` (development only)
- **Metrics**: Port 9090 (when enabled)

## 🔒 Security

- JWT token authentication
- CORS protection
- Rate limiting
- Input validation
- Environment-based secrets

## 🤝 Contributing

1. Follow the existing code structure
2. Add tests for new features
3. Update documentation
4. Use type hints
5. Follow PEP 8 style guide

## 📝 License

This project is for educational and development purposes.

---

**Next Steps:**
1. Set up your `.env` file
2. Install and configure databases
3. Run the development server
4. Check the API docs at `http://localhost:8000/docs` 