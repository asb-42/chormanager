# GitNexus Configuration for ChorManager

## Setup Complete

GitNexus has been installed and configured for this repository.

### Installation
- **GitNexus version:** 1.6.7
- **MCP package:** mcp 1.27.2 (installed in project venv)

### Index Status
- **Indexed commit:** cde3f58
- **Nodes:** 2,671
- **Edges:** 4,677
- **Clusters:** 123
- **Flows:** 144

### MCP Server
The MCP server is configured and ready. Start it with:
```bash
gitnexus mcp
```

### Available Commands

#### Query the knowledge graph
```bash
gitnexus query "search term"
```

#### Get context for a symbol
```bash
gitnexus context <SymbolName>
# Example: gitnexus context SingerRepository
```

#### Impact analysis (blast radius)
```bash
gitnexus impact <SymbolName>
# Example: gitnexus impact SingerRepository
```

#### Detect changes from git diff
```bash
gitnexus detect-changes
```

#### Generate wiki
```bash
gitnexus wiki
```

### Skills Installed (OpenCode)
1. `gitnexus-cli` - CLI usage guidance
2. `gitnexus-debugging` - Debugging assistance
3. `gitnexus-exploring` - Codebase exploration
4. `gitnexus-guide` - General guidance
5. `gitnexus-impact-analysis` - Change impact analysis
6. `gitnexus-pr-review` - PR review assistance
7. `gitnexus-refactoring` - Refactoring suggestions

### Re-indexing
After significant code changes, re-index with:
```bash
gitnexus analyze
```

### Status Check
```bash
gitnexus status
```
