# Interactive Components in Markdown

You can now embed interactive React components directly in your markdown content! Here are some examples:

## Action Buttons

Simple buttons that can perform actions:

<ActionButton action="run_code">Run Code</ActionButton>

<ActionButton action="download" variant="secondary">Download File</ActionButton>

<ActionButton url="https://github.com" variant="primary">Open GitHub</ActionButton>

## Quick Forms

Interactive forms for user input:

<QuickForm title="Enter your name" placeholder="Your name..." buttonText="Submit" action="submit_name" />

<QuickForm title="API Key" placeholder="Enter API key..." buttonText="Save" action="save_key" />

## Code Runner

Execute code snippets interactively:

<CodeRunner language="python" code="print('Hello, World!')
for i in range(3):
    print(f'Count: {i}')" />

<CodeRunner language="javascript" code="console.log('Hello from JavaScript!');
const result = [1, 2, 3].map(x => x * 2);
console.log(result);" />

## Data Fetcher

Fetch and display API data:

<DataFetcher endpoint="/api/stats" title="Get Statistics" />

<DataFetcher endpoint="/api/users" title="Fetch Users" />

## Mixed Content

You can mix regular markdown with interactive components:

Here's some **regular markdown** with `inline code`, and then an interactive button:

<ActionButton action="refresh" variant="success" size="sm">Refresh Data</ActionButton>

And here's a code block:

```python
def hello_world():
    return "Hello, World!"
```

Followed by a runner for that code:

<CodeRunner language="python" code="def hello_world():
    return 'Hello, World!'

print(hello_world())" />

## How It Works

These components are:
- **Fully interactive** - they can handle clicks, form submissions, API calls
- **Stateful** - they maintain their own state (loading, results, etc.)
- **Responsive** - they work on both mobile and desktop  
- **Customizable** - you can pass props to control behavior and appearance

The AI assistant can now generate markdown that includes these interactive elements!