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