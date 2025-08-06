/**
 * User-friendly display names for AI tools
 * Maps technical tool names to intuitive descriptions that users can understand
 */

export const TOOL_DISPLAY_NAMES: Record<string, string> = {
  // Workspace/Code Execution Tools
  'create_workspace': 'Getting things ready…',
  'upload_file': 'Processing the files…',
  'execute_code': 'Working on it…',
  
  // Memory Tools
  'retrieve_user_memory': 'Fetching more information about you…',
  'save_user_memory': 'Saving your information…',
  
  // Knowledge/Document Tools
  'search_user_uploaded_documents': 'Looking through docs in the chat…',
  'list_user_uploaded_documents': 'Listing uploaded docs…',
  
  // Web/External Tools (if any)
  'web_search': 'Searching the web for more information…',
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
