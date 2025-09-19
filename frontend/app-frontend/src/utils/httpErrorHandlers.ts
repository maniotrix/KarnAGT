// HTTP Error Handling Utilities
// Centralized error parsing and message generation for consistent UX

/**
 * Parse 429 errors and provide appropriate user-friendly messages
 * Differentiates between rate limiting and conversation locking
 */
export const handle429Error = async (response: Response): Promise<Error> => {
  try {
    const errorText = await response.text();
    let errorData;
    
    try {
      errorData = JSON.parse(errorText);
    } catch {
      // If not JSON, treat as string
      errorData = { detail: errorText };
    }
    
    // Check if it's a conversation lock (detail is object with error: "conversation_locked")
    if (errorData.detail && typeof errorData.detail === 'object' && errorData.detail.error === 'conversation_locked') {
      return new Error('Conversation busy. Please wait a moment and reload.');
    }
    
    // Check if it's rate limiting (detail is string or has error_code: "RATE_001")
    if (typeof errorData.detail === 'string' || errorData.error_code === 'RATE_001' || errorData.error_type === 'rate_limit_exceeded') {
      return new Error('Too many requests. Please wait a moment before trying again.');
    }
    
    // Fallback for unknown 429 types
    return new Error('Server busy. Please wait and try again.');
  } catch {
    // If we can't parse the error, use fallback
    return new Error('Server busy. Please wait and try again.');
  }
};

/**
 * Parse generic HTTP errors and provide user-friendly messages
 * Can be extended for other status codes as needed
 */
export const handleHttpError = async (response: Response): Promise<Error> => {
  if (response.status === 429) {
    return await handle429Error(response);
  }
  
  // Add more status code handlers here as needed
  // 401, 403, 500, etc.
  
  return new Error(`Request failed: ${response.statusText}`);
};
