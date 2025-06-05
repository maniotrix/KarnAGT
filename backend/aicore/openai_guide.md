# A Practical Guide to Building Agents

## Contents

- [Introduction](#introduction)
- [What Is an Agent?](#what-is-an-agent)
- [When Should You Build an Agent?](#when-should-you-build-an-agent)
- [Agent Design Foundations](#agent-design-foundations)
  - [Selecting Your Models](#selecting-your-models)
  - [Defining Tools](#defining-tools)
  - [Configuring Instructions](#configuring-instructions)
- [Orchestration](#orchestration)
  - [Single-Agent Systems](#single-agent-systems)
  - [Manager Pattern](#manager-pattern)
  - [Decentralized Pattern](#decentralized-pattern)
- [Guardrails](#guardrails)
  - [Types of Guardrails](#types-of-guardrails)
  - [Building Guardrails](#building-guardrails)
  - [Human Intervention](#human-intervention)
- [Conclusion](#conclusion)
- [More Resources](#more-resources)

---

## Introduction

Large language models are becoming increasingly capable of handling complex, multi-step tasks. Advances in reasoning, multimodality, and tool use have unlocked a new category of LLM-powered systems known as **agents**.

This guide is designed for product and engineering teams exploring how to build their first agents, distilling insights from numerous customer deployments into **practical and actionable** best practices. It includes frameworks for identifying promising use cases, clear patterns for designing agent logic and orchestration, and guardrails to ensure agents run safely, predictably, and effectively.

After reading this guide, you’ll have the foundational knowledge to confidently start building your first agent.

---

## What Is an Agent?

Agents are systems that **independently** accomplish tasks on your behalf.

> **Definition**: An agent leverages an LLM to manage workflow execution, make decisions, dynamically invoke tools, and recognize when a workflow is complete or needs to halt and return control to the user.

A **workflow** is a sequence of steps to meet a user’s goal—resolving a support ticket, booking a reservation, committing code, or generating reports.

**Note**: Integrations that use LLMs only for single-turn responses or classification (chatbots, sentiment analysis) are *not* agents—they don’t control full workflow execution.

---

## When Should You Build an Agent?

Agents shine where traditional deterministic automation fails:

1. **Complex decision-making**: Nuanced judgments, exceptions, or context-sensitive flows (e.g., refund approvals).
2. **Difficult-to-maintain rules**: Large, error-prone rulesets (e.g., vendor security reviews).
3. **Unstructured data reliance**: Natural language, document understanding, conversational flows (e.g., insurance claim processing).

> **Tip**: Validate your use case clearly meets these criteria; otherwise, a rule-based solution may suffice.

---

## Agent Design Foundations

An agent comprises three core components:

1. **Model**: LLM powering reasoning and decision-making.
2. **Tools**: External functions or APIs for data retrieval and actions.
3. **Instructions**: Clear guidelines and guardrails that define agent behavior.

### Selecting Your Models

- Prototype with the **most capable** model to establish a baseline.
- Use **evals** to measure performance on key tasks.
- Swap in **smaller** or faster models where accuracy remains acceptable to optimize cost and latency.

```python
# Example: instantiate a weather agent
from openai_agents import Agent, get_weather

weather_agent = Agent(
    name="Weather Agent",
    instructions="You are a helpful agent who can talk to users about the weather.",
    tools=[get_weather],
)
```

### Defining Tools

Tools extend agents’ capabilities. Standardize definitions for reusability:

| Type            | Description                                            | Examples                                              |
|-----------------|--------------------------------------------------------|-------------------------------------------------------|
| **Data**        | Retrieve context/information                           | Query database, read PDFs, web search                 |
| **Action**      | Perform operations                                     | Send emails, update CRM records, dispatch tickets     |
| **Orchestration** | Trigger other agents or workflows                     | Invoke refund agent, research agent, writing agent    |

```python
from openai_agents import Agent, WebSearchTool, function_tool

@function_tool
def save_results(output: str) -> str:
    db.insert({"output": output})
    return "Results saved"

search_agent = Agent(
    name="Search Agent",
    instructions="Help the user search the internet and save results if asked.",
    tools=[WebSearchTool(), save_results],
)
```

### Configuring Instructions

High-quality instructions reduce ambiguity:

- **Use existing docs**: Map support scripts or SOPs into numbered steps.
- **Break down tasks**: Smaller, well-defined steps.
- **Define clear actions**: Explicit tool calls and user messages.
- **Handle edge cases**: Conditional branches for missing or invalid input.

```text
“You are an expert in writing instructions for an LLM agent. Convert the following policy document into a numbered list of clear, unambiguous steps for an agent: {{policy_doc}}”
```

---

## Orchestration

Two main patterns:

1. **Single-agent systems**: One agent runs a loop, invoking tools until completion.
2. **Multi-agent systems**: Multiple specialized agents coordinate via tool calls or handoffs.

### Single-Agent Systems

A single agent can scale by adding tools. Execution is a loop until a final output or exit condition.

```python
from openai_agents import Runner, UserMessage

# Loop until agent returns a direct response or invokes a final tool
response = Runner.run(agent, [UserMessage("What's the capital of the USA?")])
print(response)
```

| Tools | Guardrails | Hooks | Instructions |
|-------|------------|-------|--------------|
| 🔧     | 🚧          | 🎣     | 📜            |

> _Exit Conditions_: final tool call, structured final output, error, or max turns.

### Manager Pattern

A central “manager” agent delegates tasks to specialized agents:

```python
from openai_agents import Agent, Runner

manager_agent = Agent(
    name="Manager",
    instructions="If asked for multiple translations, call the relevant tools.",
    tools=[
        spanish_agent.as_tool(
            tool_name="translate_to_spanish",
            tool_description="Translate user message to Spanish",
        ),
        french_agent.as_tool(
            tool_name="translate_to_french",
            tool_description="Translate user message to French",
        ),
        italian_agent.as_tool(
            tool_name="translate_to_italian",
            tool_description="Translate user message to Italian",
        ),
    ],
)

async def main():
    output = await Runner.run(manager_agent, "Translate 'hello' to Spanish, French and Italian for me!")
    print(output.new_messages)
```

### Decentralized Pattern

Agents hand off control directly to peers based on specialization:

```python
triage_agent = Agent(
    name="Triage Agent",
    instructions="Assess customer queries and delegate.",
    handoffs=[technical_support_agent, sales_agent, order_agent],
)

# Start triage flow
await Runner.run(triage_agent, "Where is my order?")
```

Flowchart (conceptual):
```
[User] -> [Triage Agent]
           |-> [Sales Agent]
           |-> [Support Agent]
           |-> [Order Agent]
```

---

## Guardrails

Layered defenses to manage privacy, safety, and brand risk:

### Types of Guardrails

- **Relevance classifier**: Flags off-topic queries.
- **Safety classifier**: Detects jailbreak attempts or injections.
- **PII filter**: Screens outputs for personal data.
- **Moderation API**: Flags harmful content.
- **Tool safeguards**: Risk ratings (low/med/high) to gate tool use.
- **Rules-based**: Blocklists, regex filters, length checks.
- **Output validation**: Brand-aligned content checks.

### Building Guardrails

1. Prioritize data privacy & content safety.
2. Add guardrails based on real-world failures.
3. Balance security with user experience.

```python
from openai_agents import Agent, Guardrail, input_guardrail, Runner

def churn_tripwire(ctx, agent, messages):
    # run churn detection agent
    result = Runner.run(churn_agent, messages)
    return result.final_output.is_churn_risk

customer_agent = Agent(
    name="Customer Support",
    instructions="Help customers with questions.",
    input_guardrails=[Guardrail(guardrail_function=churn_tripwire)],
)
```

### Human Intervention

Implement escalation for:

- **Failure thresholds**: Retries exceeded → hand off to human.
- **High-risk actions**: Refunds, cancellations → require human approval.

---

## Conclusion

Agents usher in intelligent workflow automation, handling ambiguity and end-to-end tasks. Start with strong foundations—capable models, clear tools, structured instructions—then choose orchestration patterns that match your complexity. Layer guardrails and plan for human-in-the-loop when needed.

Iterate from small deployments to robust systems. Agents don’t just automate tasks—they transform how workflows are built.

---

## More Resources

- [OpenAI API](https://openai.com/api/)
- [OpenAI for Business](https://openai.com/business/)
- [ChatGPT Enterprise](https://openai.com/chatgpt/enterprise/)
- [OpenAI Safety](https://openai.com/safety/)
- [Developer Docs](https://platform.openai.com/docs/overview/)

