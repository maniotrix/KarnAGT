# Interactive Components in Assistant Messages

## Overview

The AssistantMessage component now supports embedding interactive React components directly within markdown content. This allows the AI assistant to create rich, interactive responses that can perform actions, make API calls, and provide dynamic functionality.

## Available Components

### 1. ActionButton
Interactive buttons that can perform various actions:

```markdown
<ActionButton action="run_code">Run Code</ActionButton>
<ActionButton action="download" variant="secondary">Download</ActionButton>
<ActionButton url="https://example.com">Open Link</ActionButton>
```

**Props:**
- `action`: string - Action type ('run_code', 'download', 'refresh')
- `url`: string - External URL to open
- `variant`: 'primary' | 'secondary' | 'success' | 'danger'
- `size`: 'sm' | 'md' | 'lg'

### 2. QuickForm
Simple forms for user input:

```markdown
<QuickForm title="Enter Name" placeholder="Your name..." buttonText="Submit" />
```

**Props:**
- `title`: string - Form title
- `placeholder`: string - Input placeholder
- `buttonText`: string - Submit button text
- `action`: string - Action identifier

### 3. CodeRunner
Execute code snippets with simulated output:

```markdown
<CodeRunner language="python" code="print('Hello World')" />
```

**Props:**
- `code`: string - Code to execute
- `language`: string - Programming language

### 4. DataFetcher
Fetch and display API data:

```markdown
<DataFetcher endpoint="/api/stats" title="Get Statistics" />
```

**Props:**
- `endpoint`: string - API endpoint
- `title`: string - Component title

## How It Works

1. **Markdown Parsing**: ReactMarkdown processes the content and identifies custom components
2. **Component Mapping**: Custom components are mapped to React components in the `components` prop
3. **State Management**: Each component manages its own state (loading, results, errors)
4. **API Integration**: Components can make real API calls or simulate responses

## Usage Examples

### AI Assistant Response with Interactive Elements

```markdown
I can help you with that! Here's a Python script to solve your problem:

```python
def calculate_fibonacci(n):
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

print(calculate_fibonacci(10))
```

You can run this code directly:

<CodeRunner language="python" code="def calculate_fibonacci(n):
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

print(calculate_fibonacci(10))" />

Or download the complete script:

<ActionButton action="download" variant="secondary">Download Script</ActionButton>

Need to modify the parameters? Use this form:

<QuickForm title="Fibonacci Number" placeholder="Enter number (e.g., 10)" buttonText="Calculate" />
```

## Benefits

1. **Enhanced User Experience**: Users can interact with responses instead of just reading them
2. **Immediate Action**: No need to copy/paste code or manually navigate to external resources
3. **Dynamic Content**: Components can update based on user input or API responses
4. **Extensible**: Easy to add new interactive components as needed

## Future Extensions

- File upload components
- Data visualization charts
- Real-time collaboration tools
- Integration with external APIs
- Custom workflow builders

The AI assistant can now generate truly interactive and helpful responses!