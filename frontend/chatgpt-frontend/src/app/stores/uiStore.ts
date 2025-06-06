// UI Store - Zustand store for UI state management
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Theme = 'light' | 'dark' | 'system';

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  title: string;
  message?: string;
  duration?: number;
}

interface UiState {
  // Sidebar state
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  
  // Theme state
  theme: Theme;
  
  // Loading states
  isLoading: boolean;
  loadingMessage?: string;
  
  // Toast notifications
  toasts: ToastMessage[];
  
  // Modal states
  isSettingsOpen: boolean;
  isProfileOpen: boolean;
  
  // Actions
  setSidebarOpen: (open: boolean) => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleSidebar: () => void;
  
  setTheme: (theme: Theme) => void;
  
  setLoading: (loading: boolean, message?: string) => void;
  
  addToast: (toast: Omit<ToastMessage, 'id'>) => void;
  removeToast: (id: string) => void;
  clearToasts: () => void;
  
  setSettingsOpen: (open: boolean) => void;
  setProfileOpen: (open: boolean) => void;
}

export const useUiStore = create<UiState>()(
  persist(
    (set, get) => ({
      // Initial state
      sidebarOpen: true,
      sidebarCollapsed: false,
      theme: 'system',
      isLoading: false,
      loadingMessage: undefined,
      toasts: [],
      isSettingsOpen: false,
      isProfileOpen: false,
      
      // Sidebar actions
      setSidebarOpen: (open) =>
        set({ sidebarOpen: open }),
      
      setSidebarCollapsed: (collapsed) =>
        set({ sidebarCollapsed: collapsed }),
      
      toggleSidebar: () =>
        set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      
      // Theme actions
      setTheme: (theme) =>
        set({ theme }),
      
      // Loading actions
      setLoading: (loading, message) =>
        set({ isLoading: loading, loadingMessage: message }),
      
      // Toast actions
      addToast: (toast) => {
        const id = crypto.randomUUID();
        const newToast: ToastMessage = {
          id,
          duration: 5000, // Default 5 seconds
          ...toast,
        };
        
        set((state) => ({
          toasts: [...state.toasts, newToast],
        }));
        
        // Auto-remove toast after duration
        if (newToast.duration && newToast.duration > 0) {
          setTimeout(() => {
            get().removeToast(id);
          }, newToast.duration);
        }
      },
      
      removeToast: (id) =>
        set((state) => ({
          toasts: state.toasts.filter((toast) => toast.id !== id),
        })),
      
      clearToasts: () =>
        set({ toasts: [] }),
      
      // Modal actions
      setSettingsOpen: (open) =>
        set({ isSettingsOpen: open }),
      
      setProfileOpen: (open) =>
        set({ isProfileOpen: open }),
    }),
    {
      name: 'chatgpt-ui-store',
      // Only persist certain UI preferences
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        theme: state.theme,
      }),
    }
  )
);

// Computed selectors
export const useIsDarkMode = () => {
  const theme = useUiStore((state) => state.theme);
  
  if (theme === 'dark') return true;
  if (theme === 'light') return false;
  
  // System preference
  if (typeof window !== 'undefined') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }
  
  return false;
};

// Helper hooks for common UI patterns
export const useToast = () => {
  const addToast = useUiStore((state) => state.addToast);
  
  return {
    success: (title: string, message?: string) =>
      addToast({ type: 'success', title, message }),
    
    error: (title: string, message?: string) =>
      addToast({ type: 'error', title, message }),
    
    info: (title: string, message?: string) =>
      addToast({ type: 'info', title, message }),
    
    warning: (title: string, message?: string) =>
      addToast({ type: 'warning', title, message }),
  };
}; 