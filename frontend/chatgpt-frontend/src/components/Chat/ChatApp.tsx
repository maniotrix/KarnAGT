// ChatApp - Modern Chat Component using Clean Architecture
import React, { useState, useEffect, useRef } from 'react';
import { 
  useConversations, 
  useDeleteConversation, 
  useCreateConversation 
} from '../../app/hooks/chat';
import { useCurrentUser, useLogout } from '../../app/hooks/auth';
import { useUiStore, useToast } from '../../app/stores/uiStore';
import { Chat } from '../Chat/Chat';
import { useNavigate, useParams } from 'react-router-dom';
import { ConversationResponse } from '../../types/chat';
import { Conversation } from '../../domain/entities/Conversation';
import { 
  Menu, 
  X, 
  Plus, 
  Trash2, 
  User, 
  LogOut,
  MessageSquare,
  Crown 
} from 'lucide-react';

export const ChatApp: React.FC = () => {
  const { conversationId } = useParams<{ conversationId?: string }>();
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(conversationId || null);
  const [isCreatingConversation, setIsCreatingConversation] = useState(false);
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);
  const [showUserDropdown, setShowUserDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  // Clean Architecture Hooks
  const { data: conversations, isLoading: conversationsLoading } = useConversations();
  const { data: user } = useCurrentUser();
  const deleteConversationMutation = useDeleteConversation();
  const createConversationMutation = useCreateConversation();
  const logoutMutation = useLogout();

  // UI State from Zustand
  const sidebarOpen = useUiStore(state => state.sidebarOpen);
  const setSidebarOpen = useUiStore(state => state.setSidebarOpen);
  const toggleSidebar = useUiStore(state => state.toggleSidebar);
  const toast = useToast();

  // Update currentConversationId when URL param changes
  useEffect(() => {
    if (conversationId) {
      setCurrentConversationId(conversationId);
    } else {
      // Homepage case - no conversation ID in URL
      setCurrentConversationId(null);
    }
  }, [conversationId]);

  // Find current conversation
  const currentConversation = conversations?.find(
    conv => conv.conversationId === currentConversationId
  );
  
  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowUserDropdown(false);
      }
    };

    if (showUserDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showUserDropdown]);

  // Handle conversation creation for new messages from homepage
  const handleCreateConversationForMessage = async (messageContent: string): Promise<ConversationResponse | null> => {
    if (isCreatingConversation) return null; // Prevent double creation
    
    setIsCreatingConversation(true);
    // Store the message for auto-submission after conversation loads
    setPendingMessage(messageContent);
    
    try {
      const newConversation = await createConversationMutation.mutateAsync({
        title: messageContent.slice(0, 50) || 'New Chat'
      });
      
      // Convert Conversation entity to ConversationResponse format
      const conversationResponse = newConversation.toBackendResponse();
      
      setCurrentConversationId(conversationResponse.conversation_id);
      navigate(`/chat/${conversationResponse.conversation_id}`, { replace: true });
      setSidebarOpen(false);
      
      return conversationResponse;
    } catch (error) {
      console.error('Failed to create conversation for message:', error);
      toast.error('Failed to create conversation', 'Please try again.');
      setPendingMessage(null); // Clear pending message on error
      return null;
    } finally {
      setIsCreatingConversation(false);
    }
  };

  const handleNewChat = async () => {
    try {
      const newConversation = await createConversationMutation.mutateAsync({
        title: 'New Conversation'
      });
      // Convert Conversation entity to ConversationResponse format
      const conversationResponse = newConversation.toBackendResponse();
      setCurrentConversationId(conversationResponse.conversation_id);
      // Update URL to reflect the new conversation
      navigate(`/chat/${conversationResponse.conversation_id}`);
      setSidebarOpen(false);
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const handleSelectConversation = (conversationId: string) => {
    setCurrentConversationId(conversationId);
    // Update URL when selecting a conversation
    navigate(`/chat/${conversationId}`);
    setSidebarOpen(false);
  };

  const handleDeleteConversation = async (conversationId: string) => {
    if (window.confirm('Are you sure you want to delete this conversation?')) {
      try {
        await deleteConversationMutation.mutateAsync(conversationId);
        if (currentConversationId === conversationId) {
          setCurrentConversationId(null);
          // Navigate to root when deleting the current conversation
          navigate('/');
        }
      } catch (error) {
        console.error('Failed to delete conversation:', error);
      }
    }
  };

  const handleLogout = async () => {
    try {
      await logoutMutation.mutateAsync();
      
      // Show success toast
      toast.success('Logout successful!', 'You have been signed out successfully.');
      
      // Small delay before navigation to allow user to see the toast
      setTimeout(() => {
        navigate('/login');
      }, 1000);
    } catch (error) {
      console.error('Logout failed:', error);
      const errorMessage = error instanceof Error ? error.message : 'Logout failed';
      toast.error('Logout failed', errorMessage);
    }
  };

  const handleConversationChange = (conversation: any) => {
    if (conversation) {
      setCurrentConversationId(conversation.conversationId);
      // Update URL when conversation changes
      navigate(`/chat/${conversation.conversationId}`);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-gray-100">
      {/* Sidebar */}
      <div className={`
        fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform duration-300 ease-in-out
        lg:translate-x-0 lg:static lg:inset-0
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="flex flex-col h-full">
          {/* Sidebar Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center">
              <MessageSquare className="h-5 w-5 mr-2" />
              Conversations
            </h2>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-1 rounded-md hover:bg-gray-100 transition-colors"
            >
              <X className="h-5 w-5 text-gray-500" />
            </button>
          </div>

          {/* New Chat Button */}
          <div className="p-4 border-b border-gray-200">
            <button
              onClick={handleNewChat}
              disabled={createConversationMutation.isPending}
              className="w-full flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Plus className="h-4 w-4 mr-2" />
              {createConversationMutation.isPending ? 'Creating...' : 'New Chat'}
            </button>
          </div>

          {/* Conversations List */}
          <div className="flex-1 overflow-y-auto p-4">
            {conversationsLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            ) : conversations && conversations.length > 0 ? (
              <div className="space-y-2">
                {conversations.map(conv => (
                  <div
                    key={conv.conversationId}
                    className={`
                      group relative flex items-center p-3 rounded-lg cursor-pointer transition-colors
                      ${currentConversationId === conv.conversationId 
                        ? 'bg-blue-50 border border-blue-200' 
                        : 'hover:bg-gray-50 border border-transparent'
                      }
                    `}
                  >
                    <div
                      className="flex-1 min-w-0"
                      onClick={() => handleSelectConversation(conv.conversationId)}
                    >
                      <div className="font-medium text-gray-900 truncate">
                        {conv.title}
                      </div>
                                             <div className="text-sm text-gray-500 mt-1">
                         {conv.messageCount} messages • {conv.totalTokensUsed} tokens
                       </div>
                       <div className="text-xs text-gray-400 mt-1">
                         {conv.updatedAt.toLocaleDateString()}
                       </div>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteConversation(conv.conversationId);
                      }}
                      disabled={deleteConversationMutation.isPending}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded-md hover:bg-red-100 text-red-600 transition-opacity disabled:opacity-50"
                      title="Delete conversation"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <MessageSquare className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p>No conversations yet</p>
                <p className="text-sm">Start a new chat to begin</p>
              </div>
            )}
          </div>

          {/* User Info & Logout */}
          <div className="border-t border-gray-200 p-4">
            <div className="flex items-center space-x-3 mb-3">
              <div className="flex-shrink-0">
                {user?.hasAvatar() ? (
                  <img
                    className="h-8 w-8 rounded-full"
                    src={user.avatarUrl}
                    alt={user.getDisplayName()}
                  />
                ) : (
                  <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center">
                    <span className="text-white text-sm font-medium">
                      {user?.getInitials()}
                    </span>
                  </div>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-900 truncate">
                  {user?.getDisplayName()}
                </div>
                <div className="flex items-center text-xs text-gray-500">
                  {user?.isPremium() && (
                    <Crown className="h-3 w-3 mr-1 text-yellow-500" />
                  )}
                  {user?.subscriptionTier} plan
                </div>
              </div>
            </div>
            {/* <button
              onClick={handleLogout}
              disabled={logoutMutation.isPending}
              className="w-full flex items-center justify-center px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors disabled:opacity-50"
            >
              <LogOut className="h-4 w-4 mr-2" />
              {logoutMutation.isPending ? 'Signing out...' : 'Sign Out'}
            </button> */}
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0 lg:ml-0">
        {/* Top Bar */}
        <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center space-x-4">
            <button
              onClick={toggleSidebar}
              className="lg:hidden p-2 rounded-md hover:bg-gray-100 transition-colors"
            >
              <Menu className="h-5 w-5 text-gray-500" />
            </button>
            <h1 className="text-xl font-semibold text-gray-900">
              ChatGPT Clone
            </h1>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-600">
              Hello, {user?.getDisplayName()}
            </span>
            <div className="hidden lg:flex items-center space-x-2 relative">
              {user?.hasAvatar() ? (
                <img
                  className="h-8 w-8 rounded-full cursor-pointer hover:ring-2 hover:ring-blue-500 transition-all"
                  src={user.avatarUrl}
                  alt={user.getDisplayName()}
                  onClick={() => setShowUserDropdown(!showUserDropdown)}
                />
              ) : (
                <div 
                  className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center cursor-pointer hover:bg-blue-700 transition-colors"
                  onClick={() => setShowUserDropdown(!showUserDropdown)}
                >
                  <span className="text-white text-sm font-medium">
                    {user?.getInitials()}
                  </span>
                </div>
              )}
              
              {/* User Dropdown - Shows quota and user info */}
              {showUserDropdown && (
                <div ref={dropdownRef} className="absolute right-0 top-full mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 z-50 p-4">
                  <div className="flex items-start space-x-3 mb-3">
                    {user?.hasAvatar() ? (
                      <img
                        className="h-10 w-10 rounded-full"
                        src={user.avatarUrl}
                        alt={user.getDisplayName()}
                      />
                    ) : (
                      <div className="h-10 w-10 rounded-full bg-blue-600 flex items-center justify-center">
                        <span className="text-white text-sm font-medium">
                          {user?.getInitials()}
                        </span>
                      </div>
                    )}
                    <div>
                      <div className="font-medium">{user?.getDisplayName()}</div>
                      <div className="text-sm text-gray-500">{user?.email}</div>
                      <div className="mt-1 flex items-center">
                        <Crown className="h-3 w-3 mr-1 text-yellow-500" />
                        <span className="text-xs bg-green-100 px-2 py-0.5 rounded-full uppercase font-medium text-green-800">
                          {user?.subscriptionTier} plan
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  {/* Quota Info */}
                  <div className="mb-4">
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-600">Usage Quota</span>
                      <span className="font-medium">70%</span>
                    </div>
                    <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div className="bg-blue-600 h-full rounded-full" style={{ width: '70%' }} />
                    </div>
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>7,000 / 10,000 tokens</span>
                      <span>~$0.14 used</span>
                    </div>
                  </div>
                  
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center justify-center px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
                  >
                    <LogOut className="h-4 w-4 mr-2" />
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Chat Component */}
        <div className="flex-1 overflow-hidden">
          <Chat
            conversationId={currentConversationId ?? undefined}
            onConversationChange={handleConversationChange}
            onCreateConversationForMessage={handleCreateConversationForMessage}
            isCreatingConversation={isCreatingConversation}
            pendingMessage={pendingMessage}
            onPendingMessageSubmitted={() => setPendingMessage(null)}
          />
        </div>
      </div>

      {/* Sidebar Overlay for Mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
}; 