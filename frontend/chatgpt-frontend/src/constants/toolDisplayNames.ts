/**
 * User-friendly display names for AI tools
 * Maps technical tool names to intuitive descriptions that users can understand
 */

export const TOOL_DISPLAY_NAMES: Record<string, string> = {
  // Workspace/Code Execution Tools
  'create_workspace': '🏗️ Setting up workspace',
  'upload_file': '📁 Uploading file',
  'execute_code': '⚡ Running code',
  
  // Memory Tools
  'retrieve_user_memory': '🧠 Recalling previous context',
  'save_user_memory': '💾 Remembering important details',
  
  // Knowledge/Document Tools
  'search_user_uploaded_documents': '🔍 Searching your documents',
  'list_user_uploaded_documents': '📋 Checking your files',
  
  // Web/External Tools (if any)
  'web_search': '🌐 Searching the web',
  'fetch_url': '🔗 Fetching web content',
  
  // File Operations
  'read_file': '📖 Reading file',
  'write_file': '✍️ Writing file',
  'list_files': '📂 Browsing files',
  
  // Data Analysis
  'analyze_data': '📊 Analyzing data',
  'generate_chart': '📈 Creating visualization',
  
  // Communication
  'send_email': '📧 Sending email',
  'make_request': '🌐 Making API request',
};

/**
 * Get user-friendly display name for a tool
 * Falls back to formatted technical name if not found
 */
export const getToolDisplayName = (toolName: string): string => {
  // Check if we have a user-friendly name
  if (TOOL_DISPLAY_NAMES[toolName]) {
    return TOOL_DISPLAY_NAMES[toolName];
  }
  
  // Fallback: Convert snake_case to Title Case
  return toolName
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase());
};

/**
 * Get status-specific messages for better user understanding
 */
export const getToolStatusMessage = (toolName: string, status: string): string => {
  const baseName = TOOL_DISPLAY_NAMES[toolName] || getToolDisplayName(toolName);
  
  switch (status) {
    case 'started':
      return baseName.replace(/^[🔍🏗️📁⚡🧠💾📋🌐🔗📖✍️📂📊📈📧]+ /, '🔄 Starting: ');
    case 'running':
      return baseName;
    case 'completed':
      return baseName.replace(/^[🔍🏗️📁⚡🧠💾📋🌐🔗📖✍️📂📊📈📧]+ /, '✅ Completed: ');
    case 'error':
      return baseName.replace(/^[🔍🏗️📁⚡🧠💾📋🌐🔗📖✍️📂📊📈📧]+ /, '❌ Failed: ');
    default:
      return baseName;
  }
};
