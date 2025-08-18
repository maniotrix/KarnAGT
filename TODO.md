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
* Consider migrating knowledge module to separate FastAPI server for better scalability and isolation
* Concurreny in backend not implemented properly 