# CodeSandbox Server File Upload Limits & Criteria

Based on analysis of the CodeSandbox server configuration and code, here are the comprehensive file upload limits and restrictions:

## 📏 **Size Limits**

### Individual File Size
- **Default:** 100 MB per file
- **Environment Variable:** `MAX_FILE_SIZE_MB` (can be overridden)
- **Validation:** Both client-side and server-side validation
- **Error:** "File too large" exception if exceeded

### Workspace Total Size
- **Default:** 500 MB per workspace
- **Environment Variable:** `MAX_WORKSPACE_SIZE_MB` (can be overridden)
- **Tracks:** Combined size of all files in a workspace

### File Count per Workspace
- **Default:** 50 files maximum per workspace
- **Environment Variable:** `MAX_FILES_PER_WORKSPACE` (can be overridden)

## 🔒 **Security Restrictions**

### Filename Restrictions
- ❌ **No hidden files** (starting with `.`)
  - Prevents: `.env`, `.git`, `.ssh`, etc.
- ❌ **No path separators** (`/` or `\`)
  - Prevents: Directory traversal attacks
  - All files uploaded to workspace root only
- ❌ **No subdirectories** allowed
- ✅ **Max filename length:** 255 characters
- ✅ **Cross-platform validation** using `pathvalidate` library

### File Content Restrictions
- **No blocked file types** currently (relies on container isolation)
- **MIME type detection** based on file extension
- **Default MIME type:** `application/octet-stream` for unknown types

## ⏱️ **Timeout Limits**

### File Operations
- **Upload/Download Timeout:** 180 seconds (3 minutes)
- **Environment Variable:** `FILE_TIMEOUT_SECONDS`

### Request Handling
- **General Request Timeout:** 300 seconds (5 minutes)
- **Environment Variable:** `REQUEST_TIMEOUT_SECONDS`

## 🔄 **Concurrency Limits**

### File Operations
- **Max Concurrent File Operations:** 15
- **Max Queued File Requests:** 40
- **File Circuit Breaker Threshold:** 8 failures
- **Circuit Recovery Timeout:** 20 seconds

## 🏠 **Workspace Limits**

### Time-to-Live (TTL)
- **Default TTL:** 2 hours
- **Maximum TTL:** 24 hours
- **Auto-cleanup:** Every 30 minutes
- **Idle Timeout:** 2 hours

## 📁 **Supported Operations**

### File Types
- ✅ **All file types supported** (no type restrictions)
- ✅ **Binary files** supported
- ✅ **Text files** supported
- ✅ **Images, PDFs, CSVs, etc.** all supported

### Operations Available
- ✅ **Upload** files to workspace
- ✅ **Download** files from workspace
- ✅ **List** files in workspace
- ✅ **Auto-detection** of generated files during code execution

## 🔧 **Configuration Override**

All limits can be overridden via environment variables:

```bash
# File size limits
MAX_FILE_SIZE_MB=200                    # Individual file size
MAX_WORKSPACE_SIZE_MB=1000             # Total workspace size
MAX_FILES_PER_WORKSPACE=100            # Max files per workspace

# Timeout limits
FILE_TIMEOUT_SECONDS=300               # File operation timeout
REQUEST_TIMEOUT_SECONDS=600            # General request timeout

# Concurrency limits
MAX_CONCURRENT_FILE_OPERATIONS=20      # Concurrent file ops
MAX_QUEUED_FILE_REQUESTS=60           # Queued file requests
```

## 🔍 **Implementation Notes**

### Client-Side Validation
- The `FileService` in the backend performs client-side validation
- Default `max_size_mb=100` in `download_and_upload_file()` method
- Fails fast before attempting server upload

### Server-Side Validation
- Final validation occurs in CodeSandbox server
- Uses `pathvalidate` library for cross-platform filename validation
- Enforces security restrictions to prevent attacks

### Error Handling
- **FileTooLargeError:** When file exceeds size limit
- **FileServiceError:** For general file operation failures
- **WorkspaceNotFoundError:** When workspace doesn't exist
- **FileOperationError:** For server-side file operation issues

## 📊 **Current Usage in Codebase**

### Backend FileService
```python
# Default limit in download_and_upload_file
max_size_mb: int = 100

# AsyncHTTPClient also enforces same limit
max_size_mb: int = 100
```

### Recommendations
- Keep client-side limits aligned with server limits
- Consider implementing progress callbacks for large files
- Monitor workspace size usage to prevent hitting limits
- Use the new `AsyncHTTPClient` for better performance

---

*This analysis is based on CodeSandbox server version found in the codebase. Limits may vary in different environments or configurations.*