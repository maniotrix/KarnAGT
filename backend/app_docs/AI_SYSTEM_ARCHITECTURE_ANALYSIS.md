# AI System Architecture Analysis

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Components](#architecture-components)
3. [Backend Architecture](#backend-architecture)
4. [Frontend Architecture](#frontend-architecture)
5. [Communication Patterns](#communication-patterns)
6. [Data Storage Architecture](#data-storage-architecture)
7. [Deployment Architecture](#deployment-architecture)
8. [AI Core System](#ai-core-system)
9. [Security Architecture](#security-architecture)
10. [Development Workflow](#development-workflow)

---

## System Overview

This is a comprehensive AI-powered chat application with advanced memory management, knowledge integration, and real-time streaming capabilities. The system is built with a microservices architecture using modern web technologies, featuring dual FastAPI services: the main backend for AI orchestration and a dedicated CodeSandbox service for isolated code execution.

### High-Level System Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        React[React/TypeScript SPA]
        Redux[Zustand State Management]
        TanStack[TanStack Query]
        UI[Radix UI + Tailwind CSS]
    end
    
    subgraph "Reverse Proxy"
        Traefik[Traefik Reverse Proxy<br/>SSL Termination<br/>Load Balancing]
    end
    
    subgraph "Main Backend Service"
        FastAPI[FastAPI Main Backend<br/>Python 3.10<br/>Port: 8000]
        AICore[AI Core Engine<br/>OpenAI Agents SDK]
        Streaming[SSE Streaming Service]
    end
    
    subgraph "CodeSandbox Service"
        CodeSandbox[CodeSandbox FastAPI<br/>Python Execution Service<br/>Port: 8080]
        JupyterServer[Jupyter Server<br/>Kernel Management]
        WorkspaceAPI[Workspace API<br/>File & Execution Management]
    end
    
    subgraph "Data Layer"
        Postgres[(PostgreSQL<br/>Primary Database)]
        Redis[(Redis<br/>Cache & Sessions)]
        Qdrant[(Qdrant<br/>Vector Database)]
        Neo4j[(Neo4j<br/>Graph Database)]
        MinIO[(MinIO<br/>Object Storage)]
    end
    
    subgraph "External Services"
        OpenAI[OpenAI API<br/>GPT-4 & Embeddings]
        AWS[AWS Infrastructure<br/>EC2 & EBS]
    end
    
    React --> Traefik
    Traefik --> FastAPI
    FastAPI --> AICore
    FastAPI --> Streaming
    AICore --> CodeSandbox
    CodeSandbox --> JupyterServer
    CodeSandbox --> WorkspaceAPI
    
    AICore --> OpenAI
    FastAPI --> Postgres
    FastAPI --> Redis
    FastAPI --> Qdrant
    FastAPI --> Neo4j
    FastAPI --> MinIO
    
    AWS --> Traefik
    AWS --> Postgres
    AWS --> Redis
    AWS --> Qdrant
    AWS --> Neo4j
    AWS --> MinIO
```

---

## Architecture Components

### Core Technologies

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Frontend** | React 19.1 + TypeScript | User interface and interaction |
| **Main Backend** | FastAPI + Python 3.10 | API server and business logic |
| **Code Execution Service** | CodeSandbox FastAPI + Jupyter Server | Isolated Python execution environment |
| **AI Frameworks** | OpenAI Agents SDK + LlamaIndex | Advanced AI capabilities and RAG |
| **Authentication** | HTTP-only cookies + CSRF | Secure session management |
| **Streaming** | Server-Sent Events (SSE) | Real-time chat communication |
| **Containerization** | Docker + Docker Compose | Service orchestration |
| **Reverse Proxy** | Traefik v3.0 | SSL termination and routing |
| **Primary DB** | PostgreSQL 15+ | Structured data storage |
| **Vector DB** | Qdrant | AI embeddings and semantic search |
| **Graph DB** | Neo4j 5.26+ | Knowledge relationships |
| **Cache** | Redis 7+ | Session storage and caching |
| **File Storage** | MinIO (S3-compatible) | Document and image storage |
| **LLM Provider** | OpenAI API (GPT-4, Embeddings) | Language model and embeddings |

---

## Backend Architecture

### Service Structure

```mermaid
graph TD
    subgraph "FastAPI Application"
        Main[main.py<br/>Application Entry]
        Router[API Router<br/>Route Management]
        Middleware[Middleware Stack<br/>Auth, CORS, Rate Limiting]
    end
    
    subgraph "API Endpoints"
        Auth[Authentication<br/>/auth/*]
        Chat[Chat Management<br/>/chat/*]
        Memory[Memory System<br/>/memory/*]
        Files[File Management<br/>/files/*]
        Tools[AI Tools<br/>/tools/*]
        Analytics[Analytics<br/>/analytics/*]
    end
    
    subgraph "Core Services"
        ChatSvc[Chat Service<br/>Message Processing]
        MemorySvc[Memory Service<br/>User Context]
        KnowledgeSvc[Knowledge Service<br/>RAG & Search]
        AuthSvc[Auth Service<br/>User Management]
        StorageSvc[Storage Service<br/>File Handling]
    end
    
    subgraph "AI Core Engine"
        ConfigAgent[Configurable AI Agent]
        OpenAIAssistant[OpenAI Assistant Client]
        WorkspaceSession[Workspace Session Manager]
        ToolRegistry[Tool Registry & Execution]
        StreamingHandler[Streaming Handler]
    end
    
    Main --> Router
    Router --> Middleware
    Middleware --> Auth
    Middleware --> Chat
    Middleware --> Memory
    Middleware --> Files
    Middleware --> Tools
    Middleware --> Analytics
    
    Chat --> ChatSvc
    Memory --> MemorySvc
    Files --> KnowledgeSvc
    Auth --> AuthSvc
    Files --> StorageSvc
    
    ChatSvc --> ConfigAgent
    ConfigAgent --> OpenAIAssistant
    ConfigAgent --> WorkspaceSession
    ConfigAgent --> ToolRegistry
    ConfigAgent --> StreamingHandler
```

### Backend Directory Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── core/                   # Core configuration and shared utilities
│   │   ├── config.py          # Application configuration
│   │   ├── database.py        # Database connection management
│   │   └── security.py        # Authentication and security
│   ├── api/                    # API layer
│   │   ├── router.py          # Main API router
│   │   └── v1/                # Version 1 API endpoints
│   │       ├── endpoints/     # Route handlers
│   │       └── middleware/    # Custom middleware
│   ├── models/                 # Data models
│   │   ├── database/          # SQLAlchemy models
│   │   └── schemas/           # Pydantic schemas
│   ├── services/               # Business logic layer
│   │   ├── auth/              # Authentication services
│   │   ├── chat/              # Chat and messaging
│   │   ├── memory/            # Memory management
│   │   ├── knowledge/         # RAG and knowledge base
│   │   └── storage/           # File and media storage
│   ├── aicore/                 # AI engine core
│   │   ├── core/              # AI assistant clients
│   │   ├── agents/            # Configurable agents
│   │   ├── tools/             # AI tool implementations
│   │   └── config/            # AI system configuration
│   └── utils/                  # Utility functions
├── migrations/                 # Database migrations (Alembic)
├── docker/                     # Docker configurations
├── requirements-linux.txt      # Python dependencies
└── docker-compose.*.yml       # Container orchestration
```

---

## Frontend Architecture

### Component Architecture

```mermaid
graph TD
    subgraph "Application Layer"
        App[App.tsx<br/>Main Application]
        Routes[React Router<br/>Navigation]
        Providers[Context Providers<br/>Auth, Theme, Query]
    end
    
    subgraph "Feature Components"
        ChatApp[ChatApp<br/>Main Chat Interface]
        Auth[AuthForm<br/>Login/Register]
        Sidebar[Sidebar<br/>Conversation List]
        MessageList[MessageList<br/>Chat History]
        ChatInput[ChatInput<br/>Message Composition]
    end
    
    subgraph "State Management"
        Zustand[Zustand Stores<br/>Global State]
        TanStackQuery[TanStack Query<br/>Server State]
        LocalState[React State<br/>Component State]
    end
    
    subgraph "Services Layer"
        ChatAPI[Chat API Service<br/>Backend Communication]
        AuthService[Auth Service<br/>Authentication]
        ImageService[Image Service<br/>File Handling]
        StreamingService[Streaming Service<br/>SSE Management]
    end
    
    subgraph "UI Layer"
        RadixUI[Radix UI<br/>Component Library]
        TailwindCSS[Tailwind CSS<br/>Styling System]
        Icons[Lucide Icons<br/>Icon System]
    end
    
    App --> Routes
    Routes --> Providers
    Providers --> ChatApp
    Providers --> Auth
    
    ChatApp --> Sidebar
    ChatApp --> MessageList
    ChatApp --> ChatInput
    
    ChatApp --> Zustand
    ChatApp --> TanStackQuery
    ChatApp --> LocalState
    
    Zustand --> ChatAPI
    TanStackQuery --> AuthService
    LocalState --> ImageService
    ChatAPI --> StreamingService
    
    ChatApp --> RadixUI
    RadixUI --> TailwindCSS
    TailwindCSS --> Icons
```

### Frontend Directory Structure

```
frontend/chatgpt-frontend/src/
├── App.tsx                     # Main application component
├── main.tsx                   # React application entry point
├── components/                # React components
│   ├── Chat/                 # Chat-related components
│   │   ├── Chat.tsx         # Main chat interface
│   │   ├── MessageList.tsx  # Message display
│   │   ├── ChatInput.tsx    # Message input
│   │   └── streaming/       # Streaming components
│   ├── Auth/                 # Authentication components
│   ├── UI/                   # Reusable UI components
│   └── common/               # Shared components
├── hooks/                     # Custom React hooks
│   ├── useChat.ts           # Chat functionality
│   ├── useAuth.ts           # Authentication
│   └── queries/             # TanStack Query hooks
├── services/                  # API and external services
│   ├── api.ts               # Base API client
│   ├── chatApi.ts           # Chat API service
│   ├── authService.ts       # Authentication service
│   └── streamingService.ts  # SSE handling
├── types/                     # TypeScript type definitions
│   ├── chat.ts              # Chat-related types
│   ├── auth.ts              # Authentication types
│   └── api.ts               # API response types
├── stores/                    # Zustand stores
├── utils/                     # Utility functions
└── config/                    # Configuration files
    └── env.ts               # Environment variables
```

---

## Communication Patterns

### Frontend-Backend Communication Flow

```mermaid
sequenceDiagram
    participant F as Frontend (React)
    participant T as Traefik Proxy
    participant B as Backend (FastAPI)
    participant AI as AI Core Engine
    participant DB as Databases
    participant OpenAI as OpenAI API
    
    Note over F,OpenAI: Chat Message Flow
    
    F->>T: POST /api/v1/chat/conversations/{id}/stream
    Note over F: HTTP-only cookies + CSRF token
    T->>B: Forward request with SSL termination
    B->>B: Authenticate user via cookies
    B->>B: Validate CSRF token
    B->>DB: Store user message
    B->>AI: Initialize AI agent with configuration
    AI->>OpenAI: Stream LLM request
    
    loop Streaming Response
        OpenAI-->>AI: Token stream
        AI-->>B: Process token + tool calls
        B-->>T: SSE event
        T-->>F: Forward SSE event
        F->>F: Update UI in real-time
    end
    
    AI->>DB: Store AI response + metadata
    B-->>F: Final completion event
```

### Authentication Flow

```mermaid
sequenceDiagram
    participant F as Frontend
    participant B as Backend
    participant G as Google OAuth
    participant DB as Database
    
    Note over F,DB: Google OAuth Login Flow
    
    F->>G: Initiate Google OAuth
    G-->>F: Authorization code
    F->>B: POST /auth/google-login + code
    B->>G: Exchange code for user info
    G-->>B: User profile data
    B->>DB: Create/update user record
    B->>B: Generate JWT tokens
    B-->>F: Set HTTP-only cookies + CSRF token
    F->>F: Update authentication state
    
    Note over F,DB: Subsequent Requests
    
    F->>B: API request with cookies
    B->>B: Validate JWT from cookie
    B->>B: Check CSRF token (for mutations)
    B-->>F: Authenticated response
```

### Real-time Streaming Architecture

```mermaid
graph LR
    subgraph "Frontend Streaming"
        ChatInput[Chat Input Component]
        StreamHandler[Stream Handler]
        MessageDisplay[Message Display]
        EventSource[EventSource/Fetch Stream]
    end
    
    subgraph "Backend Streaming"
        StreamEndpoint[Stream Endpoint<br/>/chat/*/stream]
        AIAgent[AI Agent]
        StreamingService[Streaming Service]
        SSEFormatter[SSE Event Formatter]
    end
    
    subgraph "AI Processing"
        OpenAIStream[OpenAI Streaming]
        ToolExecution[Tool Execution]
        ResponseBuilder[Response Builder]
    end
    
    ChatInput --> StreamHandler
    StreamHandler --> EventSource
    EventSource --> StreamEndpoint
    
    StreamEndpoint --> AIAgent
    AIAgent --> OpenAIStream
    AIAgent --> ToolExecution
    OpenAIStream --> ResponseBuilder
    ToolExecution --> ResponseBuilder
    ResponseBuilder --> StreamingService
    StreamingService --> SSEFormatter
    
    SSEFormatter --> EventSource
    EventSource --> MessageDisplay
```

---

## Data Storage Architecture

### Database Architecture Overview

```mermaid
graph TD
    subgraph "PostgreSQL - Primary Database"
        Users[users<br/>User accounts & preferences]
        Conversations[conversations<br/>Chat sessions]
        Messages[messages<br/>Chat messages & metadata]
        MemoryPrefs[memory_preferences<br/>User memory settings]
        KnowledgeFiles[knowledge_files<br/>Uploaded file metadata]
        CostTracking[cost_tracking<br/>API usage & billing]
        ToolExecDB[tool_executions<br/>Function call logs]
    end
    
    subgraph "Redis - Caching Layer"
        Sessions[User Sessions<br/>HTTP-only cookie data]
        CacheLayer[API Response Cache<br/>Temporary data]
        CeleryBroker[Celery Task Queue<br/>Background jobs]
    end
    
    subgraph "Qdrant - Vector Database"
        ChatMemories[chat_memories<br/>Conversation embeddings]
        KnowledgeVectors[knowledge_files<br/>Document embeddings]
        UserProfiles[user_profiles<br/>Preference vectors]
    end
    
    subgraph "Neo4j - Graph Database"
        UserNodes[User Nodes<br/>User entities]
        ConceptNodes[Concept Nodes<br/>Knowledge concepts]
        RelationshipEdges[Relationships<br/>Semantic connections]
    end
    
    subgraph "MinIO - Object Storage"
        UserUploads[User Uploads<br/>Documents & images]
        GeneratedPlots[Generated Plots<br/>AI-created visualizations]
        Thumbnails[Thumbnails<br/>Image previews]
    end
    
    Users --> Sessions
    Conversations --> Messages
    Messages --> ChatMemories
    KnowledgeFiles --> KnowledgeVectors
    KnowledgeFiles --> UserUploads
    Users --> UserProfiles
    Users --> UserNodes
    Messages --> ConceptNodes
    UserNodes --> RelationshipEdges
    ConceptNodes --> RelationshipEdges
```

### Data Flow Patterns

```mermaid
flowchart TD
    subgraph "User Interaction"
        UserMessage[User sends message]
        FileUpload[User uploads file]
    end
    
    subgraph "Primary Storage (PostgreSQL)"
        StoreMessage[Store message in database]
        StoreFile[Store file metadata]
        UpdateConversation[Update conversation]
    end
    
    subgraph "Vector Processing (Qdrant)"
        GenerateEmbedding[Generate embeddings]
        StoreVectors[Store in vector database]
        SemanticSearch[Enable semantic search]
    end
    
    subgraph "Graph Processing (Neo4j)"
        ExtractEntities[Extract entities/concepts]
        BuildRelationships[Build knowledge graph]
        UpdateGraph[Update graph database]
    end
    
    subgraph "Object Storage (MinIO)"
        StoreFiles[Store files in object storage]
        GenerateThumbnails[Generate thumbnails]
        PresignedURLs[Create presigned URLs]
    end
    
    subgraph "Caching (Redis)"
        CacheResponse[Cache API responses]
        StoreSession[Store session data]
        QueueTasks[Queue background tasks]
    end
    
    UserMessage --> StoreMessage
    StoreMessage --> GenerateEmbedding
    GenerateEmbedding --> StoreVectors
    StoreVectors --> SemanticSearch
    
    FileUpload --> StoreFile
    StoreFile --> StoreFiles
    StoreFiles --> GenerateThumbnails
    StoreFiles --> GenerateEmbedding
    
    StoreMessage --> ExtractEntities
    ExtractEntities --> BuildRelationships
    BuildRelationships --> UpdateGraph
    
    StoreMessage --> CacheResponse
    UserMessage --> StoreSession
    StoreFile --> QueueTasks
```

---

## Deployment Architecture

### Development Environment

```mermaid
graph TD
    subgraph "Local Development"
        Dev[Developer Machine<br/>Windows/VSCode]
        Docker[Docker Desktop]
        LocalFiles[Local File System]
    end
    
    subgraph "Development Containers"
        TraefikDev[Traefik Dev<br/>localhost:8080]
        BackendDev[Backend Dev<br/>Hot Reload]
        FrontendDev[Frontend Dev<br/>Vite Dev Server]
        CodeSandboxDev[CodeSandbox Dev<br/>Code Execution]
    end
    
    subgraph "Development Databases"
        PostgresDev[PostgreSQL Dev<br/>localhost:5432]
        RedisDev[Redis Dev<br/>localhost:6379]
        QdrantDev[Qdrant Dev<br/>localhost:6333]
        Neo4jDev[Neo4j Dev<br/>localhost:7687]
        MinioDev[MinIO Dev<br/>localhost:9000]
    end
    
    Dev --> Docker
    Docker --> TraefikDev
    Docker --> BackendDev
    Docker --> FrontendDev
    Docker --> CodeSandboxDev
    Docker --> PostgresDev
    Docker --> RedisDev
    Docker --> QdrantDev
    Docker --> Neo4jDev
    Docker --> MinioDev
    
    TraefikDev --> BackendDev
    BackendDev --> CodeSandboxDev
    BackendDev --> PostgresDev
    BackendDev --> RedisDev
    BackendDev --> QdrantDev
    BackendDev --> Neo4jDev
    BackendDev --> MinioDev
```

### Production Deployment (AWS)

```mermaid
graph TD
    subgraph "AWS Infrastructure"
        ELB[Elastic Load Balancer<br/>SSL Termination]
        EC2[EC2 Instance<br/>t3.large or larger]
        EBS[EBS Volumes<br/>Persistent Storage]
        ElasticIP[Elastic IP<br/>Static IP Address]
        SecurityGroups[Security Groups<br/>Firewall Rules]
    end
    
    subgraph "Container Orchestration"
        TraefikProd[Traefik Production<br/>Reverse Proxy]
        BackendProd[Backend Production<br/>Scaled Containers]
        FrontendProd[Frontend Production<br/>Static Build]
        CodeSandboxProd[CodeSandbox Production<br/>Isolated Execution]
    end
    
    subgraph "Database Services"
        PostgresProd[PostgreSQL Prod<br/>EBS Volume 10GB]
        RedisProd[Redis Prod<br/>EBS Volume 10GB]
        QdrantProd[Qdrant Prod<br/>EBS Volume 50GB]
        Neo4jProd[Neo4j Prod<br/>EBS Volume 10GB]
        MinioProd[MinIO Prod<br/>EBS Volume 10GB]
    end
    
    subgraph "Monitoring & Logging"
        Logs[Centralized Logging<br/>JSON Format]
        HealthChecks[Health Monitoring<br/>Container Status]
        Backups[Automated Backups<br/>Volume Snapshots]
    end
    
    ElasticIP --> ELB
    ELB --> EC2
    EC2 --> SecurityGroups
    EC2 --> EBS
    
    EC2 --> TraefikProd
    TraefikProd --> BackendProd
    TraefikProd --> FrontendProd
    BackendProd --> CodeSandboxProd
    
    BackendProd --> PostgresProd
    BackendProd --> RedisProd
    BackendProd --> QdrantProd
    BackendProd --> Neo4jProd
    BackendProd --> MinioProd
    
    PostgresProd --> EBS
    RedisProd --> EBS
    QdrantProd --> EBS
    Neo4jProd --> EBS
    MinioProd --> EBS
    
    EC2 --> Logs
    TraefikProd --> HealthChecks
    EBS --> Backups
```

### Container Architecture

```mermaid
graph LR
    subgraph "Network: dev-network/prod-network"
        subgraph "Web Tier"
            Traefik[Traefik<br/>:80, :443<br/>Reverse Proxy]
        end
        
        subgraph "Application Tier"
            Backend[FastAPI Backend<br/>:8000<br/>AI Processing]
        end
        
        subgraph "Execution Tier"
            CodeSandbox[CodeSandbox Service<br/>:8080<br/>Isolated Python Runtime]
            JupyterKernels[Jupyter Kernels<br/>Workspace Management]
        end
        
        subgraph "Data Tier"
            Postgres[PostgreSQL<br/>:5432<br/>Primary DB]
            Redis[Redis<br/>:6379<br/>Cache & Queue]
            Qdrant[Qdrant<br/>:6333<br/>Vector DB]
            Neo4j[Neo4j<br/>:7687<br/>Graph DB]
            MinIO[MinIO<br/>:9000<br/>Object Storage]
        end
    end
    
    subgraph "External"
        Frontend[Frontend<br/>React SPA<br/>Served by Traefik]
        OpenAI[OpenAI API<br/>External Service]
    end
    
    Frontend --> Traefik
    Traefik --> Backend
    Backend --> CodeSandbox
    CodeSandbox --> JupyterKernels
    Backend --> OpenAI
    
    Backend --> Postgres
    Backend --> Redis
    Backend --> Qdrant
    Backend --> Neo4j
    Backend --> MinIO
```

---

## AI Core System

### AI Agent Architecture

```mermaid
graph TD
    subgraph "AI Core Engine"
        ConfigManager[Configuration Manager<br/>Agent Settings]
        AgentFactory[Agent Factory<br/>Dynamic Creation]
        ToolRegistry[Tool Registry<br/>Available Functions]
    end
    
    subgraph "Configurable Agent"
        BaseAgent[Base AI Agent]
        CodeAgent[Code Executor Agent<br/>Programming Tasks]
        MemoryAgent[Memory Agent<br/>Context Retention]
        KnowledgeAgent[Knowledge Agent<br/>RAG Integration]
    end
    
    subgraph "Tool System"
        CodeExecution[Code Execution<br/>Python/JavaScript]
        FileTools[File Operations<br/>Read/Write/Search]
        MemoryTools[Memory Tools<br/>Store/Recall]
        SearchTools[Search Tools<br/>Vector/Semantic]
        WebTools[Web Tools<br/>Browse/Scrape]
    end
    
    subgraph "Execution Environment"
        WorkspaceSession[Workspace Session<br/>Isolated Container]
        StreamingHandler[Streaming Handler<br/>Real-time Output]
        SafetyGuards[Safety Guards<br/>Content Filtering]
    end
    
    subgraph "External AI Services"
        OpenAIAPI[OpenAI API<br/>GPT-4 Models]
        EmbeddingAPI[Embedding API<br/>text-embedding-3]
    end
    
    ConfigManager --> AgentFactory
    AgentFactory --> BaseAgent
    BaseAgent --> CodeAgent
    BaseAgent --> MemoryAgent
    BaseAgent --> KnowledgeAgent
    
    CodeAgent --> ToolRegistry
    ToolRegistry --> CodeExecution
    ToolRegistry --> FileTools
    ToolRegistry --> MemoryTools
    ToolRegistry --> SearchTools
    ToolRegistry --> WebTools
    
    CodeAgent --> WorkspaceSession
    CodeAgent --> StreamingHandler
    CodeAgent --> SafetyGuards
    
    CodeAgent --> OpenAIAPI
    MemoryAgent --> EmbeddingAPI
    KnowledgeAgent --> EmbeddingAPI
```

### AI Processing Flow

```mermaid
sequenceDiagram
    participant U as User
    participant C as Chat Service
    participant A as AI Agent
    participant T as Tool Registry
    participant W as Workspace
    participant O as OpenAI API
    participant DB as Database
    
    U->>C: Send message
    C->>A: Initialize configurable agent
    A->>A: Load agent configuration
    A->>A: Build instruction context
    A->>O: Stream LLM request
    
    loop Streaming Response
        O-->>A: Token + tool calls
        A->>T: Execute tool if needed
        T->>W: Run in isolated environment
        W-->>T: Tool execution result
        T-->>A: Return formatted result
        A-->>C: Stream token/result
        C-->>U: Update UI real-time
    end
    
    A->>DB: Store conversation + metadata
    A->>DB: Update memory + knowledge
    A-->>C: Final response
    C-->>U: Complete message
```

---

## Security Architecture

### Authentication & Authorization

```mermaid
graph TD
    subgraph "Authentication Layer"
        GoogleOAuth[Google OAuth 2.0<br/>Third-party login]
        JWTTokens[JWT Tokens<br/>Access & Refresh]
        HTTPCookies[HTTP-only Cookies<br/>Secure storage]
        CSRFTokens[CSRF Tokens<br/>Mutation protection]
    end
    
    subgraph "Authorization Layer"
        RoleBasedAuth[Role-based Access<br/>User permissions]
        ResourceAuth[Resource Authorization<br/>Data ownership]
        RateLimit[Rate Limiting<br/>API throttling]
    end
    
    subgraph "Security Middleware"
        AuthMiddleware[Authentication Middleware<br/>Token validation]
        CORSMiddleware[CORS Middleware<br/>Cross-origin requests]
        SecurityHeaders[Security Headers<br/>HSTS, CSP, etc.]
        UserContext[User Context<br/>Request scoping]
    end
    
    subgraph "Data Protection"
        EncryptionAtRest[Encryption at Rest<br/>Database encryption]
        EncryptionInTransit[Encryption in Transit<br/>HTTPS/TLS]
        SecretsManagement[Secrets Management<br/>Environment variables]
        InputValidation[Input Validation<br/>Pydantic schemas]
    end
    
    GoogleOAuth --> JWTTokens
    JWTTokens --> HTTPCookies
    HTTPCookies --> CSRFTokens
    
    CSRFTokens --> AuthMiddleware
    AuthMiddleware --> RoleBasedAuth
    AuthMiddleware --> ResourceAuth
    AuthMiddleware --> RateLimit
    
    AuthMiddleware --> CORSMiddleware
    CORSMiddleware --> SecurityHeaders
    SecurityHeaders --> UserContext
    
    UserContext --> EncryptionAtRest
    UserContext --> EncryptionInTransit
    UserContext --> SecretsManagement
    UserContext --> InputValidation
```

### Security Implementation

| Layer | Implementation | Purpose |
|-------|---------------|---------|
| **Transport** | HTTPS/TLS + Traefik SSL | Encrypt data in transit |
| **Authentication** | Google OAuth + JWT | Verify user identity |
| **Session Management** | HTTP-only cookies | Secure token storage |
| **CSRF Protection** | Double-submit cookies | Prevent cross-site attacks |
| **Authorization** | Role-based + resource ownership | Control access to data |
| **Input Validation** | Pydantic schemas | Sanitize user input |
| **Rate Limiting** | Redis-based throttling | Prevent abuse |
| **Container Security** | Non-root users + isolation | Limit container privileges |
| **Secrets Management** | Environment variables | Secure credential storage |
| **Data Encryption** | PostgreSQL encryption | Protect data at rest |

---

## Development Workflow

### Development Environment Setup

```mermaid
flowchart TD
    subgraph "Setup Phase"
        CloneRepo[Clone Repository<br/>Git checkout]
        EnvConfig[Configure Environment<br/>.env files]
        InstallDeps[Install Dependencies<br/>Python + Node.js]
    end
    
    subgraph "Database Setup"
        StartDatabases[Start Database Services<br/>docker-compose up]
        RunMigrations[Run Database Migrations<br/>Alembic upgrade]
        SeedData[Seed Test Data<br/>Optional]
    end
    
    subgraph "Application Startup"
        StartBackend[Start Backend<br/>FastAPI dev server]
        StartFrontend[Start Frontend<br/>Vite dev server]
        StartServices[Start Additional Services<br/>CodeSandbox, etc.]
    end
    
    subgraph "Development Tools"
        HotReload[Hot Reload<br/>Automatic restarts]
        DebugTools[Debug Tools<br/>Logging & profiling]
        APITesting[API Testing<br/>FastAPI docs]
    end
    
    CloneRepo --> EnvConfig
    EnvConfig --> InstallDeps
    InstallDeps --> StartDatabases
    StartDatabases --> RunMigrations
    RunMigrations --> SeedData
    SeedData --> StartBackend
    StartBackend --> StartFrontend
    StartFrontend --> StartServices
    StartServices --> HotReload
    HotReload --> DebugTools
    DebugTools --> APITesting
```

### Deployment Pipeline

```mermaid
graph LR
    subgraph "Development"
        LocalDev[Local Development<br/>Feature branches]
        Testing[Local Testing<br/>Unit & integration]
        Commit[Git Commit<br/>Version control]
    end
    
    subgraph "CI/CD Pipeline"
        BuildImages[Build Docker Images<br/>Multi-stage builds]
        RunTests[Automated Testing<br/>pytest + Jest]
        SecurityScan[Security Scanning<br/>Vulnerability check]
        ImageRegistry[Push to Registry<br/>Docker Hub/ECR]
    end
    
    subgraph "Deployment Stages"
        Staging[Staging Environment<br/>Pre-production testing]
        Production[Production Environment<br/>AWS deployment]
        Monitoring[Health Monitoring<br/>Alerts & metrics]
    end
    
    LocalDev --> Testing
    Testing --> Commit
    Commit --> BuildImages
    BuildImages --> RunTests
    RunTests --> SecurityScan
    SecurityScan --> ImageRegistry
    ImageRegistry --> Staging
    Staging --> Production
    Production --> Monitoring
```

### Configuration Management

```mermaid
graph TD
    subgraph "Environment Configurations"
        DevEnv[Development<br/>.env.local]
        StagingEnv[Staging<br/>.env.staging]
        ProdEnv[Production<br/>.env.production]
    end
    
    subgraph "Docker Configurations"
        DevCompose[docker-compose.dev.yml<br/>Local development]
        StagingCompose[docker-compose.staging.yml<br/>Staging environment]
        ProdCompose[docker-compose.prod.yml<br/>Production deployment]
    end
    
    subgraph "Application Settings"
        BackendConfig[Backend Configuration<br/>FastAPI settings]
        FrontendConfig[Frontend Configuration<br/>Environment variables]
        DatabaseConfig[Database Configuration<br/>Connection strings]
        AIConfig[AI Configuration<br/>Model & agent settings]
    end
    
    DevEnv --> DevCompose
    StagingEnv --> StagingCompose
    ProdEnv --> ProdCompose
    
    DevCompose --> BackendConfig
    DevCompose --> FrontendConfig
    DevCompose --> DatabaseConfig
    DevCompose --> AIConfig
```

---

## AI Core System Deep Dive

### How AI Gets Its Advanced Capabilities

The AI system's sophisticated capabilities come from a multi-layered architecture combining several specialized systems:

#### 1. **Tool Registry & Execution Framework**

```mermaid
graph TD
    subgraph "Tool Registry System"
        Registry[Tool Registry<br/>Central Management]
        MemoryTools[Memory Tools<br/>User Context]
        KnowledgeTools[Knowledge Tools<br/>Document Search]
        CodeTools[Code Execution Tools<br/>Python Environment]
        WebTools[Web Search Tools<br/>Internet Access]
    end
    
    subgraph "AI Agent Integration"
        Agent[Configurable AI Agent]
        Instructions[Instruction Builder<br/>Prompt Engineering]
        StreamHandler[Streaming Handler<br/>Real-time Response]
    end
    
    Registry --> MemoryTools
    Registry --> KnowledgeTools
    Registry --> CodeTools
    Registry --> WebTools
    
    Agent --> Registry
    Instructions --> Agent
    Agent --> StreamHandler
```

**Tool Registration Process:**

- Tools are dynamically registered at startup using factory patterns
- Each tool type (memory, knowledge, code, web) has specialized implementations
- Tools are resolved by name during agent execution
- Runtime parameters are passed to tool factories for customization

#### 2. **Code Execution Capabilities**

The AI gets its code execution powers through a sophisticated workspace system:

**CodeSandbox Service Architecture:**
The code execution system runs as a separate containerized service:

```python
# CodeSandbox Service - Isolated execution environment
class CodeSandboxService:
    """
    Dedicated service for code execution with:
    - Separate Docker container (port 8080)
    - Isolated Jupyter kernel environments per workspace
    - Persistent workspace sessions
    - Secure file system isolation
    - Resource limits and timeout controls
    - Rich output capture (plots, dataframes, images)
    """

@function_tool(strict_mode=False)
async def execute_code(workspace_id: str, code: str, timeout: int = 60):
    """
    Execute Python code via CodeSandbox service:
    - Routes to dedicated CodeSandbox container
    - Maintains persistent Jupyter kernel per workspace
    - Variables and imports persist across executions
    - Generated files saved to workspace
    - Standard output/error captured and returned
    """
```

**Key Features:**

- **Separate Container Service**: CodeSandbox runs as dedicated service on port 8080
- **Isolated Workspaces**: Each conversation gets its own workspace in the container
- **Persistent State**: Variables and imports survive between code executions within workspace
- **File Management**: Full file I/O operations with workspace-scoped persistence
- **Rich Output Support**: Matplotlib plots, pandas dataframes, images automatically captured
- **Security Sandbox**: Code execution completely isolated from main backend
- **Timeout Controls**: Prevents runaway executions with configurable limits
- **Resource Management**: Memory and CPU limits enforced at container level

#### 3. **Document Search & Knowledge Capabilities**

The AI's document processing uses a sophisticated RAG (Retrieval-Augmented Generation) system:

**Knowledge Service Architecture:**
```python
class KnowledgeService:
    """
    High-level service for knowledge file operations.
    Features:
    - Multi-format document parsing (PDF, DOCX, TXT, etc.)
    - Vector embeddings using OpenAI text-embedding-3-small
    - Semantic search with Qdrant vector database
    - Document chunking and metadata extraction
    - Query-time retrieval and ranking
    """
```

**Document Processing Pipeline:**
1. **File Upload** → Documents stored in MinIO object storage
2. **Content Extraction** → Text extracted from various formats
3. **Chunking** → Documents split into semantic chunks
4. **Vectorization** → Text converted to embeddings
5. **Storage** → Vectors stored in Qdrant with metadata
6. **Query Processing** → User queries matched against vectors
7. **Context Assembly** → Relevant chunks retrieved and ranked

**Search Modes:**
- **Conversation-wide Search**: Query all documents in a conversation
- **Specific File Search**: Target particular documents by ID
- **Semantic Similarity**: Vector-based content matching
- **Metadata Filtering**: Filter by document type, date, etc.

#### 4. **Web Search Integration**

The AI system integrates web search as a primary capability:

**Implementation Details:**
- **Priority System**: Web search is the default tool for most queries
- **Intelligent Routing**: Automatic detection of web search intent
- **Safety Measures**: Content filtering and source validation
- **Cost Controls**: Limited searches per conversation turn
- **Result Processing**: Extract and synthesize information from multiple sources

**Web Search Decision Logic:**
```python
# From prompt_utils.py - Web search is mandated by default
"""
MANDATORY: Use `web_search_preview` to verify information and get current data, EXCEPT when:
- Query needs explicit tool (code execution, document query, memory operation)
- Query is creative/fictional task that doesn't require factual accuracy
- Query contains personal/private information
- Query is follow-up/clarification in ongoing conversation
"""
```

#### 5. **Memory System Architecture**

The AI's memory capabilities use a sophisticated 6-bucket system:

**Memory Buckets:**
```python
MEMORY_BUCKETS = {
    "identity": "User's name, role, location, personal info",
    "preferences": "Communication style, tools, formats they like", 
    "goals": "Current projects, learning objectives, targets",
    "workflows": "Habits, routines, processes they follow",
    "capabilities": "Skills, experience, hardware, constraints",
    "social": "Team members, colleagues, relationships"
}
```

**Memory Operations:**

- **Storage**: Automatic extraction and storage during conversations
- **Retrieval**: Context-aware memory search and ranking
- **Importance Weighting**: 0.0-1.0 importance scoring system
- **Expiration**: Configurable memory retention policies
- **Access Patterns**: Track memory usage and update relevance

**Memory Integration in AI Responses:**
```python
async def get_essential_user_context(memory_service, user_id) -> str:
    """
    Get essential user memories formatted as a string for system prompt context.
    Only includes high-importance memories (>= 0.7) from key buckets.
    Provides AI with user background without overwhelming token budget.
    """
```

### Context Engineering & Prompt Architecture

#### 1. **Advanced Context Building System**

The AI uses sophisticated context engineering to manage conversation history:

```mermaid
graph TD
    subgraph "Context Management"
        ContextBuilder[Conversation Context Builder]
        TokenCounter[Token Counter<br/>Track Usage]
        Summarizer[Conversation Summarizer<br/>Compress History]
        OverflowHandler[Overflow Handler<br/>Manage Limits]
    end
    
    subgraph "Context Components"
        Summary[Historical Summary<br/>Compressed Past]
        Recent[Recent Messages<br/>Full Context]
        Memory[User Memory<br/>Personal Context]
        Files[Attached Files<br/>Multimodal Content]
    end
    
    subgraph "Context Assembly"
        FinalContext[Final Context<br/>Structured for AI]
        TokenLimit[40K Token Limit<br/>GPT-4 Optimization]
    end
    
    ContextBuilder --> TokenCounter
    TokenCounter --> OverflowHandler
    OverflowHandler --> Summarizer
    
    ContextBuilder --> Summary
    ContextBuilder --> Recent
    ContextBuilder --> Memory
    ContextBuilder --> Files
    
    Summary --> FinalContext
    Recent --> FinalContext
    Memory --> FinalContext
    Files --> FinalContext
    
    FinalContext --> TokenLimit
```

**Context Building Strategy:**
1. **Token Counting**: Every message is analyzed for token usage
2. **Overflow Detection**: When context exceeds 40K tokens, summarization triggers
3. **Intelligent Summarization**: Older messages compressed while preserving key information
4. **Recent Message Preservation**: Most recent exchanges kept in full detail
5. **Memory Integration**: User-specific context automatically included
6. **Multimodal Support**: Images and documents integrated into context

#### 2. **Sophisticated Prompt Engineering**

The system uses multi-layered prompt engineering:

**Core Prompt Structure:**
```python
# Base instruction foundation
INITIAL_CORE_PROMPT = """
You are an intelligent and helpful AI assistant. 
You always strictly use web search to improve your answers.
Core capabilities include:
- Always searching the web before giving any answer
- Answering questions with accurate, up-to-date information
- Problem-solving and strategic thinking
- Creative ideation and brainstorming
"""

# Advanced tool integration prompts
ALL_TOOLS_ENABLED_SYSTEM_PROMPT = """
🚨 MANDATORY CODE BLOCK RULE: Use exactly 4 backticks for ALL code blocks
🚨 CRITICAL - LINKS RULE: ALWAYS format links as markdown [text](url)

DEFAULT TOOL SELECTION HIERARCHY:
Step 1: Explicit Tool Cues (HIGHEST PRIORITY)
Step 2: Internet keywords → web search
Step 3: Default behavior → web search unless timeless
"""
```

**Prompt Engineering Principles:**
- **Tool Prioritization**: Clear hierarchy for tool selection
- **Safety Instructions**: Explicit rules for handling different content types
- **Formatting Standards**: Consistent output formatting requirements
- **Error Handling**: Graceful degradation when tools fail
- **Token Budget Management**: Cost-aware tool usage limits

#### 3. **Dynamic Instruction Generation**

The AI uses dynamic instruction building based on context:

```python
class InstructionBuilder:
    async def build_instructions(self, context: InstructionContext) -> str:
        """
        Build complete instructions with automatic memory context
        - Start with core prompt
        - Add user-specific memory context
        - Include tool availability information
        - Customize based on user preferences
        """
```

**Instruction Customization:**
- **User Memory Integration**: Personal context automatically included
- **Tool Availability**: Dynamic tool descriptions based on configuration
- **Preference Adaptation**: Instruction style adapted to user preferences
- **Context Sensitivity**: Instructions modified based on conversation state

### Software Engineering Practices Behind the System

#### 1. **Configuration-Driven Architecture**

The entire AI system is built around sophisticated configuration management:

```python
@dataclass
class AIConfig:
    """Complete AI system configuration"""
    agent: AgentConfig          # Agent behavior and capabilities
    model: ModelConfig          # LLM model selection and parameters
    runner: RunnerConfig        # Execution and streaming settings
    tools: ToolConfig           # Available tools and their settings
    config_version: str = "1.0" # Configuration versioning
```

**Key Practices:**
- **Centralized Configuration**: All AI behavior controlled by configuration
- **Environment-specific Settings**: Different configs for dev/staging/prod
- **Runtime Configuration Updates**: Dynamic reconfiguration without restarts
- **Validation Systems**: Configuration validation before deployment
- **Version Management**: Configuration versioning and migration support

#### 2. **Advanced Error Handling & Resilience**

The system implements comprehensive error handling:

**Error Handling Strategies:**
- **Graceful Degradation**: When tools fail, system continues with alternatives
- **Circuit Breakers**: Prevent cascade failures in tool execution
- **Retry Logic**: Automatic retry for transient failures
- **Fallback Mechanisms**: Alternative approaches when primary methods fail
- **Comprehensive Logging**: Detailed error tracking and debugging

#### 3. **Performance Optimization Practices**

**Optimization Techniques:**
- **Async Processing**: Full async/await implementation throughout
- **Connection Pooling**: Database and external service connection management
- **Caching Strategies**: Multi-level caching (Redis + in-memory)
- **Streaming Architecture**: Real-time response delivery
- **Resource Management**: Memory cleanup and garbage collection
- **Token Optimization**: Intelligent context management to minimize API costs

#### 4. **Security-First Development**

**Security Practices:**
- **Sandboxed Execution**: Code execution in isolated containers
- **Input Validation**: Comprehensive input sanitization
- **Authentication Integration**: Secure user context management
- **Audit Logging**: Complete audit trail for all operations
- **Rate Limiting**: Protection against abuse and resource exhaustion

#### 5. **Monitoring & Observability**

**Observability Features:**
- **Structured Logging**: JSON logs with correlation IDs
- **Performance Metrics**: Response times, token usage, error rates
- **Health Checks**: Comprehensive service health monitoring
- **Tracing**: Distributed tracing across service boundaries
- **Cost Tracking**: Detailed API usage and cost monitoring

---

## System Capabilities

### Core Features

| Feature | Implementation | Status |
|---------|---------------|---------|
| **Real-time Chat** | SSE streaming with OpenAI integration | ✅ Implemented |
| **Memory Management** | 6-bucket system with vector embeddings | ✅ Implemented |
| **File Processing** | Multi-format RAG with semantic search | ✅ Implemented |
| **Code Execution** | Sandboxed Jupyter kernel workspaces | ✅ Implemented |
| **Knowledge RAG** | Qdrant vector database + OpenAI embeddings | ✅ Implemented |
| **Web Search** | Mandatory web search with intelligent routing | ✅ Implemented |
| **User Authentication** | Google OAuth + HTTP-only cookies + CSRF | ✅ Implemented |
| **Multi-database** | PostgreSQL + Redis + Qdrant + Neo4j | ✅ Implemented |
| **Containerized** | Docker + Docker Compose orchestration | ✅ Implemented |
| **Production Ready** | AWS deployment + comprehensive monitoring | ✅ Implemented |

### AI Capabilities Deep Dive

#### **Core AI Technologies**
- **OpenAI Agents SDK**: Foundation for advanced reasoning and tool execution
- **LlamaIndex**: RAG framework for document processing and knowledge management
- **Qdrant Vector Database**: Semantic search and similarity matching
- **CodeSandbox FastAPI Service**: Dedicated Python execution environment with Jupyter

#### **Tool System Architecture**
- **Dynamic Tool Registry**: Runtime tool registration and resolution
- **Tool Factories**: Parameterized tool creation for different contexts
- **Tool Prioritization**: Intelligent tool selection based on user intent
- **Error Recovery**: Fallback mechanisms when tools fail
- **Resource Management**: Tool execution limits and cleanup

#### **Memory Intelligence**
- **Contextual Storage**: Automatic extraction of important information
- **Relevance Scoring**: Importance-based memory ranking (0.0-1.0)
- **Bucket Organization**: 6-category system for organized memory
- **Expiration Management**: Automatic cleanup of outdated information
- **Context Integration**: Seamless memory integration in responses

#### **Knowledge Processing**
- **Multi-format Support**: PDF, DOCX, TXT, CSV, JSON, HTML, etc.
- **Intelligent Chunking**: Semantic document segmentation
- **Vector Embeddings**: OpenAI text-embedding-3-small integration
- **Semantic Search**: Context-aware document retrieval
- **Source Attribution**: Detailed source tracking and citation

#### **Code Execution Security**
- **Workspace Isolation**: Container-based execution environments
- **State Persistence**: Variables maintained across executions
- **Output Capture**: Rich media output support (plots, tables, etc.)
- **Timeout Controls**: Execution time limits for safety
- **Resource Limits**: Memory and CPU usage constraints

#### **Web Search Integration**
- **Default Priority**: Web search as primary information source
- **Intent Detection**: Automatic routing based on query analysis
- **Source Validation**: Authority-based source ranking
- **Content Synthesis**: Multi-source information integration
- **Cost Optimization**: Query limits and result caching

### Scalability Features

- **Horizontal Scaling**: Container-based architecture supports load balancing
- **Database Optimization**: Connection pooling and indexed queries
- **Multi-level Caching**: Redis + in-memory caching strategy
- **Async Processing**: Full async/await implementation
- **Resource Management**: Memory limits and automatic cleanup
- **Stream Processing**: Real-time response delivery with backpressure
- **Load Balancing**: Traefik reverse proxy with health checks

---

## Conclusion

This AI system represents a comprehensive, production-ready chat application with advanced AI capabilities. The architecture successfully combines:

1. **Modern Web Technologies**: React/TypeScript frontend with FastAPI backend
2. **Real-time Communication**: SSE-based streaming for immediate user feedback
3. **Advanced AI Integration**: Configurable agents with tool execution capabilities
4. **Multi-database Architecture**: Optimized data storage for different use cases
5. **Security-first Design**: Comprehensive authentication and authorization
6. **Container Orchestration**: Docker-based deployment with environment parity
7. **Production Deployment**: AWS-ready infrastructure with monitoring

The system's modular design allows for easy extension and maintenance while providing a robust foundation for AI-powered applications.
