 # 🏗️ **Clean Architecture Implementation Plan**

## **🎯 Architecture Overview**

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │    Pages    │  │ Components  │  │     UI Hooks        │ │
│  │             │  │             │  │                     │ │
│  │ - ChatPage  │  │ - ChatMsg   │  │ - useTheme          │ │
│  │ - AuthPage  │  │ - ChatInput │  │ - useLocalStorage   │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Use Cases   │  │   Services  │  │   Query Hooks       │ │
│  │             │  │             │  │                     │ │
│  │ - SendMsg   │  │ - ChatSvc   │  │ - useChatQuery      │ │
│  │ - AuthUser  │  │ - AuthSvc   │  │ - useAuthQuery      │ │
│  │ - LoadConv  │  │ - ConvSvc   │  │ - useConvQuery      │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     DOMAIN LAYER                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Entities   │  │ Interfaces  │  │   Domain Events     │ │
│  │             │  │             │  │                     │ │
│  │ - Message   │  │ - IChatRepo │  │ - MessageSent       │ │
│  │ - User      │  │ - IAuthRepo │  │ - UserSignedIn      │ │
│  │ - Convrstn  │  │ - IConvRepo │  │ - ConversationNew   │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 INFRASTRUCTURE LAYER                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │Repositories │  │ API Clients │  │   External APIs     │ │
│  │             │  │             │  │                     │ │
│  │ - ChatRepo  │  │ - HttpClient│  │ - FastAPI Backend   │ │
│  │ - AuthRepo  │  │ - WSClient  │  │ - OpenAI API        │ │
│  │ - ConvRepo  │  │ - Storage   │  │ - Local Storage     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## **📁 Proposed Directory Structure**

```
src/
├── app/                          # Application Layer
│   ├── hooks/                    # React Query hooks
│   │   ├── auth/
│   │   │   ├── useAuth.ts
│   │   │   ├── useLogin.ts
│   │   │   └── useSignup.ts
│   │   ├── chat/
│   │   │   ├── useChat.ts
│   │   │   ├── useSendMessage.ts
│   │   │   └── useConversations.ts
│   │   └── index.ts
│   ├── services/                 # Business Logic Services
│   │   ├── AuthService.ts
│   │   ├── ChatService.ts
│   │   ├── ConversationService.ts
│   │   └── NotificationService.ts
│   ├── stores/                   # Client State (Zustand)
│   │   ├── authStore.ts
│   │   ├── uiStore.ts
│   │   ├── chatStore.ts
│   │   └── index.ts
│   └── use-cases/                # Application Use Cases
│       ├── auth/
│       │   ├── LoginUser.ts
│       │   ├── RegisterUser.ts
│       │   └── LogoutUser.ts
│       ├── chat/
│       │   ├── SendMessage.ts
│       │   ├── LoadConversation.ts
│       │   └── CreateConversation.ts
│       └── index.ts
│
├── domain/                       # Domain Layer
│   ├── entities/                 # Business Entities
│   │   ├── User.ts
│   │   ├── Message.ts
│   │   ├── Conversation.ts
│   │   └── index.ts
│   ├── interfaces/               # Repository Interfaces
│   │   ├── IAuthRepository.ts
│   │   ├── IChatRepository.ts
│   │   ├── IConversationRepository.ts
│   │   └── index.ts
│   ├── events/                   # Domain Events
│   │   ├── MessageSent.ts
│   │   ├── UserSignedIn.ts
│   │   └── index.ts
│   └── types/                    # Domain Types
│       ├── AuthTypes.ts
│       ├── ChatTypes.ts
│       └── index.ts
│
├── infrastructure/               # Infrastructure Layer
│   ├── repositories/             # Repository Implementations
│   │   ├── AuthRepository.ts
│   │   ├── ChatRepository.ts
│   │   ├── ConversationRepository.ts
│   │   └── index.ts
│   ├── api/                      # API Clients
│   │   ├── HttpClient.ts
│   │   ├── WebSocketClient.ts
│   │   ├── endpoints/
│   │   │   ├── authEndpoints.ts
│   │   │   ├── chatEndpoints.ts
│   │   │   └── index.ts
│   │   └── index.ts
│   ├── storage/                  # Storage Adapters
│   │   ├── LocalStorageAdapter.ts
│   │   ├── SessionStorageAdapter.ts
│   │   └── index.ts
│   └── config/                   # Configuration
│       ├── env.ts
│       ├── api.ts
│       └── index.ts
│
├── presentation/                 # Presentation Layer
│   ├── components/               # Reusable Components
│   │   ├── ui/                   # UI Components (Radix UI wrappers)
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Dialog.tsx
│   │   │   └── index.ts
│   │   ├── forms/                # Form Components
│   │   │   ├── LoginForm.tsx
│   │   │   ├── SignupForm.tsx
│   │   │   ├── MessageForm.tsx
│   │   │   └── index.ts
│   │   ├── chat/                 # Chat-specific Components
│   │   │   ├── ChatMessage.tsx
│   │   │   ├── ChatInput.tsx
│   │   │   ├── ConversationList.tsx
│   │   │   └── index.ts
│   │   └── common/               # Common Components
│   │       ├── Header.tsx
│   │       ├── Sidebar.tsx
│   │       ├── Loading.tsx
│   │       └── index.ts
│   ├── pages/                    # Page Components
│   │   ├── ChatPage.tsx
│   │   ├── AuthPage.tsx
│   │   ├── SettingsPage.tsx
│   │   └── index.ts
│   ├── hooks/                    # UI-specific Hooks
│   │   ├── useTheme.ts
│   │   ├── useLocalStorage.ts
│   │   ├── useDebounce.ts
│   │   └── index.ts
│   └── layouts/                  # Layout Components
│       ├── AppLayout.tsx
│       ├── AuthLayout.tsx
│       └── index.ts
│
├── shared/                       # Shared Utilities
│   ├── utils/                    # Pure Functions
│   │   ├── date.ts
│   │   ├── validation.ts
│   │   ├── formatting.ts
│   │   └── index.ts
│   ├── constants/                # Application Constants
│   │   ├── routes.ts
│   │   ├── messages.ts
│   │   └── index.ts
│   ├── schemas/                  # Zod Validation Schemas
│   │   ├── authSchemas.ts
│   │   ├── chatSchemas.ts
│   │   └── index.ts
│   └── types/                    # Shared Types
│       ├── api.ts
│       ├── common.ts
│       └── index.ts
│
└── App.tsx                       # Main App Component
```

## **🔧 Implementation Strategy**

### **Phase 2A: Repository Pattern (Day 4)**
1. **Create Domain Entities**
   - `User`, `Message`, `Conversation` entities
   - Repository interfaces (`IAuthRepository`, `IChatRepository`)

2. **Implement Repository Pattern**
   - Move current API logic to repositories
   - Abstract data access behind interfaces

### **Phase 2B: Use Cases Layer (Day 5)**
1. **Extract Business Logic**
   - Create use cases for `SendMessage`, `LoginUser`, etc.
   - Remove business logic from components

2. **Implement Services**
   - `AuthService`, `ChatService`, `ConversationService`
   - Coordinate between repositories and use cases

### **Phase 2C: Query Hooks Refactor (Day 6)**
1. **TanStack Query Integration**
   - Create query hooks that use repositories
   - Separate server state from client state

2. **Zustand State Management**
   - UI state (`theme`, `sidebar open/closed`)
   - App state (`current conversation`, `typing state`)

### **Phase 2D: Component Refactor (Day 7)**
1. **Pure Components**
   - Components only handle presentation
   - Props down, events up pattern

2. **Smart vs Dumb Components**
   - Smart: Use query hooks and stores
   - Dumb: Pure presentation components

## **✅ Benefits of This Architecture**

### **1. Testability**
```typescript
// Easy to mock repositories
const mockChatRepo = {
  sendMessage: vi.fn(),
  getConversations: vi.fn()
}
```

### **2. Maintainability**
- Clear separation of concerns
- Easy to find and modify business logic
- Consistent patterns across the app

### **3. Scalability**
- Easy to add new features
- Domain logic independent of UI
- Can swap implementations easily

### **4. Performance**
- TanStack Query for efficient server state
- Zustand for lightweight client state
- Optimized re-renders

## **📊 Migration Plan**

| **Day** | **Task** | **Focus** |
|---------|----------|-----------|
| **4** | Repository Pattern | Move API logic to repositories |
| **5** | Use Cases & Services | Extract business logic |
| **6** | Query Hooks Refactor | TanStack Query + Zustand |
| **7** | Component Refactor | Clean component architecture |
| **8** | Testing & Validation | Ensure architecture works |

This clean architecture will make the ChatGPT Clone:
- **More maintainable** - Clear separation of concerns
- **More testable** - Easy to mock dependencies  
- **More scalable** - Easy to add features
- **More performant** - Optimized state management