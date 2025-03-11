# Memory System

The Agentic Office PM system uses LangMem to implement a sophisticated memory system that enables persistent context, shared knowledge, and self-improvement capabilities.

## Overview

LangMem provides the foundation for storing and retrieving information across conversations and between different specialized agents. This enables Smith to:

- Remember user preferences and past interactions
- Share knowledge between specialized agents
- Maintain context across different conversation threads
- Improve performance through reflection and learning

## Memory Architecture

### Store Implementation

The system uses an `InMemoryStore` as the foundation for memory storage:

```python
self.store = InMemoryStore()
```

While this implementation keeps memories in RAM, the architecture supports swapping in other store implementations (like vector databases) without changing the application logic.

### Namespace Structure

Memories are organized in a hierarchical namespace structure: 