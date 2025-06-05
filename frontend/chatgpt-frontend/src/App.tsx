import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Chat } from './components/Chat/Chat';
import { ConversationResponse } from './types/chat';
import { chatApi } from './services/chatApi';
import './App.css';

// Login/Register Form Component
const AuthForm: React.FC = () => {
  const { login, register, isLoading, error, clearError } = useAuth();
  const [isLoginMode, setIsLoginMode] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirm_password: '',
    full_name: '',
    username: '',
  });
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // Password validation function
  const validatePassword = (password: string) => {
    const errors: string[] = [];
    
    if (password.length < 8) {
      errors.push('At least 8 characters');
    }
    if (!/[A-Z]/.test(password)) {
      errors.push('One uppercase letter');
    }
    if (!/[a-z]/.test(password)) {
      errors.push('One lowercase letter');
    }
    if (!/\d/.test(password)) {
      errors.push('One number');
    }
    
    return errors;
  };

  // Form validation
  const validateForm = () => {
    const errors: Record<string, string> = {};

    if (!formData.email) {
      errors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      errors.email = 'Email is invalid';
    }

    if (!formData.password) {
      errors.password = 'Password is required';
    } else if (!isLoginMode) {
      const passwordErrors = validatePassword(formData.password);
      if (passwordErrors.length > 0) {
        errors.password = `Password must have: ${passwordErrors.join(', ')}`;
      }
    }

    if (!isLoginMode) {
      if (!formData.confirm_password) {
        errors.confirm_password = 'Password confirmation is required';
      } else if (formData.password !== formData.confirm_password) {
        errors.confirm_password = 'Passwords do not match';
      }

      if (formData.username && formData.username.length < 3) {
        errors.username = 'Username must be at least 3 characters';
      }
      if (formData.username && !/^[a-zA-Z0-9_-]+$/.test(formData.username)) {
        errors.username = 'Username can only contain letters, numbers, hyphens, and underscores';
      }
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setValidationErrors({});

    // Validate form
    if (!validateForm()) {
      return;
    }
    
    try {
      if (isLoginMode) {
        await login({
          email: formData.email,
          password: formData.password,
        });
      } else {
        await register({
          email: formData.email,
          password: formData.password,
          confirm_password: formData.confirm_password,
          full_name: formData.full_name,
          username: formData.username,
        });
      }
    } catch (err) {
      // Error handled by auth context
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  return (
    <div className="auth-container">
      <div className="auth-form">
        <div className="auth-header">
          <h1>ChatGPT Clone</h1>
          <p>{isLoginMode ? 'Sign in to your account' : 'Create a new account'}</p>
        </div>

        {error && (
          <div className="auth-error">
            {error}
            <button onClick={clearError} className="error-close">×</button>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={formData.email}
              onChange={(e) => handleInputChange('email', e.target.value)}
              required
              disabled={isLoading}
              className={validationErrors.email ? 'error' : ''}
            />
            {validationErrors.email && (
              <div className="field-error">{validationErrors.email}</div>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="password">
              Password
              {!isLoginMode && (
                <span className="password-hint">
                  (8+ chars, uppercase, lowercase, number)
                </span>
              )}
            </label>
            <input
              id="password"
              type="password"
              value={formData.password}
              onChange={(e) => handleInputChange('password', e.target.value)}
              required
              disabled={isLoading}
              className={validationErrors.password ? 'error' : ''}
            />
            {validationErrors.password && (
              <div className="field-error">{validationErrors.password}</div>
            )}
          </div>

          {!isLoginMode && (
            <>
              <div className="form-group">
                <label htmlFor="confirm_password">Confirm Password</label>
                <input
                  id="confirm_password"
                  type="password"
                  value={formData.confirm_password}
                  onChange={(e) => handleInputChange('confirm_password', e.target.value)}
                  required
                  disabled={isLoading}
                  className={validationErrors.confirm_password ? 'error' : ''}
                />
                {validationErrors.confirm_password && (
                  <div className="field-error">{validationErrors.confirm_password}</div>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="full_name">Full Name (optional)</label>
                <input
                  id="full_name"
                  type="text"
                  value={formData.full_name}
                  onChange={(e) => handleInputChange('full_name', e.target.value)}
                  disabled={isLoading}
                />
              </div>

              <div className="form-group">
                <label htmlFor="username">Username (optional)</label>
                <input
                  id="username"
                  type="text"
                  value={formData.username}
                  onChange={(e) => handleInputChange('username', e.target.value)}
                  disabled={isLoading}
                  className={validationErrors.username ? 'error' : ''}
                  placeholder="letters, numbers, - and _ only"
                />
                {validationErrors.username && (
                  <div className="field-error">{validationErrors.username}</div>
                )}
              </div>
            </>
          )}

          <button
            type="submit"
            className="auth-submit"
            disabled={isLoading}
          >
            {isLoading ? 'Please wait...' : (isLoginMode ? 'Sign In' : 'Sign Up')}
          </button>
        </form>

        <div className="auth-switch">
          <button
            type="button"
            onClick={() => setIsLoginMode(!isLoginMode)}
            className="switch-mode"
            disabled={isLoading}
          >
            {isLoginMode ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
          </button>
        </div>
      </div>
    </div>
  );
};

// Main Chat App Component
const ChatApp: React.FC = () => {
  const { user, logout } = useAuth();
  const [conversations, setConversations] = useState<ConversationResponse[]>([]);
  const [currentConversation, setCurrentConversation] = useState<ConversationResponse | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      const convs = await chatApi.getConversations();
      setConversations(convs);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const handleConversationChange = (conversation: ConversationResponse | null) => {
    setCurrentConversation(conversation);
    if (conversation) {
      // Update or add to conversations list
      setConversations(prev => {
        const existing = prev.find(c => c.conversation_id === conversation.conversation_id);
        if (existing) {
          return prev.map(c => 
            c.conversation_id === conversation.conversation_id ? conversation : c
          );
        } else {
          return [conversation, ...prev];
        }
      });
    }
  };

  const handleNewChat = () => {
    setCurrentConversation(null);
    setSidebarOpen(false);
  };

  const handleSelectConversation = (conversation: ConversationResponse) => {
    setCurrentConversation(conversation);
    setSidebarOpen(false);
  };

  const handleDeleteConversation = async (conversationId: string) => {
    if (window.confirm('Are you sure you want to delete this conversation?')) {
      try {
        await chatApi.deleteConversation(conversationId);
        setConversations(prev => prev.filter(c => c.conversation_id !== conversationId));
        if (currentConversation?.conversation_id === conversationId) {
          setCurrentConversation(null);
        }
      } catch (error) {
        console.error('Failed to delete conversation:', error);
      }
    }
  };

  return (
    <div className="chat-app">
      {/* Sidebar */}
      <div className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-header">
          <h2>Conversations</h2>
          <button onClick={() => setSidebarOpen(false)} className="sidebar-close">×</button>
        </div>

        <button onClick={handleNewChat} className="new-chat-button">
          + New Chat
        </button>

        <div className="conversations-list">
          {conversations.map(conv => (
            <div
              key={conv.conversation_id}
              className={`conversation-item ${
                currentConversation?.conversation_id === conv.conversation_id ? 'active' : ''
              }`}
            >
              <div
                className="conversation-content"
                onClick={() => handleSelectConversation(conv)}
              >
                <div className="conversation-title">{conv.title}</div>
                <div className="conversation-meta">
                  {conv.message_count} messages • {conv.total_tokens_used} tokens
                </div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteConversation(conv.conversation_id);
                }}
                className="delete-conversation"
                title="Delete conversation"
              >
                🗑️
              </button>
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <div className="user-info">
            <div className="user-name">{user?.full_name || user?.email}</div>
            <div className="user-tier">{user?.subscription_tier} plan</div>
          </div>
          <button onClick={logout} className="logout-button">
            Sign Out
          </button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="main-content">
        <div className="top-bar">
          <button
            onClick={() => setSidebarOpen(true)}
            className="sidebar-toggle"
          >
            ☰
          </button>
          <h1>ChatGPT Clone</h1>
          <div className="top-bar-actions">
            <span className="user-greeting">
              Hello, {user?.full_name || user?.email}
            </span>
          </div>
        </div>

        <Chat
          conversationId={currentConversation?.conversation_id}
          onConversationChange={handleConversationChange}
        />
      </div>

      {/* Sidebar overlay for mobile */}
      {sidebarOpen && (
        <div
          className="sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
};

// Main App Component with Auth Provider
const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

// App content that can access auth context
const AppContent: React.FC = () => {
  const { isAuthenticated, isLoading, isInitialized } = useAuth();

  // Show loading during auth initialization or any loading state
  if (!isInitialized || isLoading) {
    return (
      <div className="app-loading">
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Initializing...</p>
        </div>
      </div>
    );
  }

  return isAuthenticated ? <ChatApp /> : <AuthForm />;
};

export default App;
