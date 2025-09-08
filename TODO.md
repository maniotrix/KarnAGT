* implement feature where usre select block of text from assistant response and add it as extra context
  like we can do in chatgpt...like whataspp reply to feature

* use agents as tools for wrapping several tools like coding tools, and removing bloated prompt for main llm (priority)

* use claude for coding tasks
* use gemini for rag tasks and any tasks which involves larger context window
* use openai for general purpose tasks and reasoning

* we built user global knowledge base in background as soon as possible and update the progress in chatgpt clone
  * there should be also quick lookup knowledge data(which basically stores keywords, titles)...just like we humans
    , when we first hear about something, recall these keywords from our memory, and then find the details or relationships to it...eg...I am given name Abhishek...what comes into my mind when this words hits my brain...I remember a friend named, abhishek and his image instantly...then consecutively I fetch all the details related to hime from my memory. And all these stuff happen within seconds. I did not search my whole memory...a quick keyword recall...and then related step by step knowledge recall whether to recall more and more unitll I have enough data for current query to answer
    [Discussion](https://chatgpt.com/g/g-p-68461b947d108191a40ccd644ced9cb8-chatgpt-clone/c/686b8246-442c-8013-a8e2-39c03607b579?model=o3)

* The context builder currently adds all images and previous chat history each message content as kind of user input - 
  ``` 
  if enhanced_content and enhanced_content.strip():
              content_parts.append({"type": "input_text", "text": enhanced_content})
          
          # Add images
          for file_id in openai_file_ids:
              content_parts.append({
                  "type": "input_image", 
                  "file_id": file_id
              })
          
          logger.info(f"Built multimodal {role} message with {len(openai_file_ids)} images and {len(knowledge_file_ids)} knowledge files and {'text' if enhanced_content.strip() else 'no text'}")
          return {
              "role": role,
              "content": content_parts
          }
  ```
  * This creates a choking problem in llm inference when it has lots of images...
    we might need to convert image inference into a tool for llm to search and understand previous images in the conversation.
    [Refer to this cursor chat](https://github.com/maniotrix/ChatGPT_Clone/blob/32defcbed44af17aacb0125263397eac004c6d26/.cursor_chats/cursor_debugging_delay_in_hello_user_re.md)
  * Also  I think the agent cant process using openai vision if provided just image url or in general any publicly available file download link in chat
  
* [PRIORITY] llm executing code without workspace, unnecessary multiple execute code calls(advice to do maximum stuff in one tool call and script), llm using code or knowledge tool when asked for internet search...completely messing up tools
* llm keeps doing:  Workspace not found: Workspace ws_abc123 not found
* llm showing made up and wrong url even if its not returned after code execution : http://localhost:8080/api/v1/workspace/ws_e4f852ac/files/abhilasha_6_april_ticket.pdf---removed create workspace tool from llm tools to avoid this

* maybe the long messages in chat collapsible

* llm trying to directly download proxy file in code sanbox instead of uploading again - {Error: ConnectionError: HTTPConnectionPool(host='localhost', port=8000): Max retries exceeded with url: /api/v1/proxy/images/img_8d9d8724} -fixed by llm system prompt

* Fix nested or raw markdown inside llm response on frontend - fixed by llm system prompt

* [PERFORMANCE] Implement Celery for knowledge service document processing to prevent FastAPI blocking
  - ✅ CONFIRMED: LlamaIndex properly handles non-blocking execution with FastAPI
  - ✅ CONFIRMED: Uses multiprocessing (not threads) so FastAPI event loop remains free
  - ✅ ANALYSIS: Current architecture supports concurrent users during document processing
  - 📋 CELERY_MIGRATION.md: Comprehensive implementation plan ready with Hidden Celery Integration
  - 🎯 PRIORITY: Celery will improve resource isolation and worker management
* Consider migrating knowledge module to separate FastAPI server for better scalability and isolation
* Concurreny in backend not implemented properly
* Need to revisit proxy url generation/access/display internally as well as publicly.
  - uses 127.0.0.1 for transforming internally, COMPLETED: Universal network architecture - 127.0.0.1 internal URL resolution + HOST config cleanup implemented
* need to revisit minio routing(external as well internal) in docker and in general in chrome
* llm using knowledge search tool instead of web search
* fix frontend input typing slow and stuck and laggy and also improve chrome action to paint latency in chrome dev tools
* recheck bcrypt issue in prod container via registering new user
* make sure REQUIRE_EMAIL_VERIFICATION=false in the production env file for backend, as its not implemented yet in backend
* add google sign in
* create essential pages on frontend
* create tech document for whole thing
* rename knowldege tools
* improve typing ui and ux on frontend
* add email verification , celery asap
* add chat search

* [RACE CONDITION] Fix file upload URL generation timing issue
  - Frontend calls bulk-presigned-urls immediately after backend returns message with file_ids
  - Backend DB transaction not yet committed when URL request arrives → "Access denied" errors
  - Solution: Include presigned URLs directly in message response to eliminate separate API call
  - Affects: Every new message with image attachments - (.curosr_chats/cursor_check_logs_for_issues_and_errors.md)

* on frontend somehow image ur download link from llm is rendered in ai message and no download link to show/click

* [MOBILE UI FIXES] Fixed sidebar auto-opening on mobile reload and page scrollability
  - Sidebar now starts closed on mobile (<1024px screens) and open on desktop
  - Added responsive window resize/orientation handling
  - Added mobile backdrop overlay to close sidebar
  - Fixed viewport meta tag to prevent zoom/scroll issues
  - Status: COMPLETED

* [CONVERSATION LOADING] Fixed missing loading state when switching chats from sidebar
  - Added isLoadingConversation state to useChat hook during conversation fetch
  - Disabled chat input and file upload during conversation loading
  - Added loading overlay with spinner for visual feedback
  - Added "Loading conversation..." placeholder text in input
  - Prevents UI interactions until conversation is fully loaded
  - Status: COMPLETED

* [BROWSER COMPATIBILITY FIXES] Fixed potential breaking issues from recent changes
  - Fixed crypto.randomUUID() fallback for older browsers (Safari <15.4, Chrome <92)
  - Removed restrictive viewport settings (user-scalable=no) for better accessibility  
  - Event listeners properly cleaned up to prevent memory leaks
  - Complex loading state logic tested and validated
  - Status: COMPLETED

* frontend issue...authorise required showing when relaoding page
* autofocus keybaord issue

* [CRITICAL BUG ANALYSIS] FileNotDecryptedError - Silent PDF Processing Failures  
  - 🔍 IDENTIFIED: PDFs fail processing with FileNotDecryptedError but users get no feedback
  - 📋 ROOT CAUSE: Password-protected PDFs, corrupted files, unsupported encryption
  - ❌ CURRENT FLOW: Upload succeeds → Processing fails silently → 0 chunks created → No LLM context
  - ✅ CONVERSATION CONTEXT: Correctly excludes failed files (prevents AI hallucination)  
  - 🚨 USER IMPACT: Users don't know why their documents aren't being processed
  - 💡 SOLUTIONS: 
    - Better error handling with specific FileNotDecryptedError catches
    - OCR fallback for problematic PDFs
    - Real-time streaming feedback (see below)
    - Detailed error messages: "PDF appears password-protected, try unlocked version"

* [HIGH PRIORITY] Send back events via streaming handler during file processing to provide real-time feedback to users
  - 🎯 PURPOSE: Transform "black box" processing into transparent user experience  
  - 📊 CURRENT: Processing happens silently for 2-5 minutes with no user feedback
  - 🔧 IDENTIFIED NEED: FileNotDecryptedError and other failures happen invisibly to users
  - 💬 STREAMING EVENTS NEEDED:
    - File Upload Progress: "📄 Processing 3 uploaded files..."
    - Processing Stages: "⬇️ Downloading file_name.pdf..." → "🔍 Processing PDF document..." → "📝 Creating document chunks..." → "🧠 Generating embeddings..."
    - Error Feedback: "❌ file_name.pdf failed - PDF appears password protected. Please try unlocked PDF"
    - Success Confirmation: "✅ file_name.pdf processed - 15 document chunks created"
  - 🎨 FRONTEND: Enhanced event handling for file_processing event type with progress indicators
  - 🏗️ BACKEND: Integration with existing streaming_callback in attachment_service.py
  - 📈 IMPACT: Users will immediately understand processing status and can take action on errors

  * add a reload buttin in header to the left beside profile info to reload current chat - Done
  * Use ai image capabilities to also create and index images uploaded by user

* Memory about atleast user name not avaialble when user first signed up in llm context. But llm can succesfully update and create new memories for user.(.cursor_chats/cursor_understanding_user_information_i.md)
* limit code sandbox container cpu ram - done
* setting openai model name from envs
* show thinking tokens on ui
* ✅ FIXED: Mobile file selection issue - cant select some files like csv, md on mobile from frontend while attaching
  - ✅ SOLUTION: Updated UniversalFileUpload.tsx to use MIME types alongside file extensions  
  - ✅ ADDED: Proper MIME type support (text/csv, text/markdown, etc.) for mobile browser compatibility
  - ✅ ADDED: Missing .md and .html file support in accept attribute
  - ✅ ENHANCED: File icon mapping for .md and .html files
  - 🔧 TECHNICAL: Mobile browsers prefer MIME types over file extensions in accept attribute
  - 📱 IMPACT: CSV, MD, HTML, and other document files now selectable on mobile devices

* pwa install -don
* add search in chat app
* use api key for user registration set in fronetend env and backend env...hence register requires a proper api key to process registration request
* app backend now not much scalable because we put uvicorn workers 1 because of our architecture problems
* maybe also increase code sandbox timeout to 60 seconds in prod env