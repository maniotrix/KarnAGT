import React from 'react';
import { Chat } from './components/Chat';
import { APP_CONFIG, CHAT_CONFIG } from './utils/constants';
import './App.css';

function App() {
  // Configure the chat with our settings
  const chatConfig = {
    api: '/api/chat', // This will be our proxy endpoint
    maxMessages: APP_CONFIG.MAX_MESSAGES_PER_CONVERSATION,
    enableCostTracking: true,
    onError: (error: Error) => {
      console.error('Chat Error:', error);
      // Here you could add error tracking service
    },
    onFinish: (message: any, options: any) => {
      console.log('Message completed:', { message, options });
      // Here you could add analytics tracking
    },
  };

  return (
    <div className="App">
      <Chat 
        config={chatConfig}
        className="main-chat"
      />
      
      {/* Footer */}
      <footer className="app-footer">
        <p>
          {APP_CONFIG.NAME} v{APP_CONFIG.VERSION} | 
          Powered by {CHAT_CONFIG.DEFAULT_MODEL}
        </p>
      </footer>
    </div>
  );
}

export default App;
