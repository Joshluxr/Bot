# ClaudeKit Implementation Plan

## Executive Summary

ClaudeKit is a comprehensive toolkit for enhancing Claude Code (and other AI coding agents) with structured workflows, specialized agents, commands, hooks, and skills. This document analyzes the Engineer and Marketing packages and provides a detailed implementation plan.

---

## Package Analysis

### 1. ClaudeKit Engineer Package (50.6MB)

**Purpose:** Software development workflow enhancement

#### Directory Structure:
```
.claude/
├── agents/           # 14 specialized AI sub-agents
├── commands/         # Slash commands for common tasks
├── hooks/            # Event-driven automation scripts
├── rules/            # Workflow and coding standards
├── skills/           # 50+ domain-specific skill modules
├── settings.json     # Claude Code configuration
├── statusline.cjs    # Custom status line display
└── scripts/          # Utility scripts
```

#### Key Agents:
| Agent | Purpose |
|-------|---------|
| `planner` | Creates implementation plans with TODO tasks |
| `code-reviewer` | Reviews code quality and standards |
| `tester` | Writes and runs comprehensive tests |
| `debugger` | Analyzes bugs and CI/CD failures |
| `docs-manager` | Maintains documentation |
| `researcher` | Conducts technical research |
| `fullstack-developer` | Full-stack implementation |
| `ui-ux-designer` | UI/UX design guidance |
| `brainstormer` | Ideation and brainstorming |

#### Key Skills (50+):
- `code-review`, `debug`, `fix` - Code quality
- `planning`, `sequential-thinking` - Problem solving
- `frontend-development`, `backend-development` - Full stack
- `git`, `devops` - Operations
- `ai-multimodal`, `ai-artist` - AI capabilities
- `mcp-builder`, `mcp-management` - MCP integration
- `docs-seeker`, `research` - Documentation
- `web-testing`, `databases` - Infrastructure

#### Hooks System:
- **SessionStart**: Initialize session, load context
- **SubagentStart**: Initialize sub-agents
- **UserPromptSubmit**: Apply dev rules, usage awareness
- **PreToolUse**: Scout blocking, privacy protection
- **PostToolUse**: Simplification reminders, usage tracking

---

### 2. ClaudeKit Marketing Package (342MB)

**Purpose:** Marketing, content, and business development

#### Skills:
| Skill | Purpose |
|-------|---------|
| `marketing-ideas` | Generate marketing strategies |
| `marketing-psychology` | Persuasion and conversion |
| `pricing-strategy` | Pricing optimization |
| `launch-strategy` | Product launch planning |
| `competitor-alternatives` | Competitive analysis |
| `paid-ads` | Advertising campaigns |
| `form-cro` | Form conversion optimization |
| `onboarding-cro` | User onboarding optimization |
| `ab-test-setup` | A/B testing frameworks |
| `ui-ux-pro-max` | Advanced UI/UX design |
| `ai-artist` | AI image generation prompts |

---

## Implementation Recommendations

### Phase 1: Core Installation (Immediate)

#### 1.1 Install ClaudeKit Engineer Globally
```bash
# Extract to ~/.claude (global Claude Code config)
unzip /tmp/claudekit-engineer.zip -d /tmp/
cp -r /tmp/claudekit-analysis/claudekit-engineer-main/.claude/* ~/.claude/

# Install skill dependencies
cd ~/.claude/skills && ./install.sh
```

#### 1.2 Configure Settings
Merge `settings.json` with existing config:
- Enable hooks system
- Configure status line
- Set up pre/post tool hooks

### Phase 2: Terragon-OSS Integration

#### 2.1 Create Project-Specific CLAUDE.md
Adapt the ClaudeKit workflow for terragon-oss:

```markdown
# CLAUDE.md for Terragon-OSS

## Role
You are a senior software engineer working on the Terragon-OSS codebase.

## Workflows
- Follow `./.claude/rules/primary-workflow.md`
- Development rules: `./.claude/rules/development-rules.md`

## Codebase Context
- Monorepo: Turborepo + pnpm
- Backend: Drizzle ORM, PostgreSQL, Redis
- Frontend: Next.js 15, React 19, Tailwind
- Sandbox: E2B, Daytona providers
- Real-time: PartyKit WebSockets

## Key Directories
- `apps/www` - Main web application
- `packages/shared` - Shared models and utilities
- `packages/sandbox` - Sandbox abstraction
- `packages/daemon` - Agent daemon
```

#### 2.2 Custom Commands for Terragon
Create project-specific commands:

| Command | Purpose |
|---------|---------|
| `/sandbox-test` | Test sandbox provider integration |
| `/db-migrate` | Run Drizzle migrations |
| `/build-check` | Run turbo build with type checking |
| `/deploy-preview` | Deploy to preview environment |

#### 2.3 Integrate Key Skills
Priority skills for terragon-oss:
1. `backend-development` - API and service logic
2. `databases` - PostgreSQL/Redis operations
3. `code-review` - Quality assurance
4. `debug` - Issue investigation
5. `devops` - CI/CD and deployment
6. `web-testing` - E2E and unit tests

### Phase 3: Hook Configuration

#### 3.1 Privacy Protection
Configure `privacy-block.cjs` for:
- `.env` files
- Credential files
- API keys

#### 3.2 Scout Blocking
Configure `scout-block.cjs` to:
- Prevent accidental large file reads
- Block binary file access
- Limit context bloat

#### 3.3 Development Rules Reminder
Customize `dev-rules-reminder.cjs` for:
- Terragon coding standards
- Monorepo conventions
- Test requirements

### Phase 4: Marketing Skills (Optional)

If marketing/content work needed:
```bash
# Extract marketing skills
unzip /tmp/claudekit-marketing.zip -d /tmp/
cp -r /tmp/claudekit-marketing-main/.agent/skills/* ~/.claude/skills/
```

---

## Configuration Details

### settings.json Structure
```json
{
  "includeCoAuthoredBy": false,
  "statusLine": {
    "type": "command",
    "command": "node .claude/statusline.cjs"
  },
  "hooks": {
    "SessionStart": [...],
    "UserPromptSubmit": [...],
    "PreToolUse": [...],
    "PostToolUse": [...]
  }
}
```

### Environment Variables
Required in `.claude/.env`:
```bash
# API Keys for skills
GEMINI_API_KEY=xxx          # For ai-multimodal
OPENAI_API_KEY=xxx          # For ai-artist
ANTHROPIC_API_KEY=xxx       # For advanced reasoning

# Optional
GITHUB_TOKEN=xxx            # For gh CLI integration
```

---

## Workflow Integration

### Primary Development Flow
1. **Planning**: Use `/plan` command with `planner` agent
2. **Research**: Parallel `researcher` agents gather context
3. **Implementation**: Follow plan, activate relevant skills
4. **Testing**: `tester` agent validates changes
5. **Review**: `code-reviewer` ensures quality
6. **Documentation**: `docs-manager` updates docs

### Skill Activation
Skills are activated on-demand:
```
Use `debug` skill for investigating the sandbox timeout issue.
```

### Agent Delegation
Delegate complex tasks:
```
Delegate to `code-reviewer` agent to review the circuit breaker implementation.
```

---

## File Locations Summary

| Component | Global Path | Project Path |
|-----------|-------------|--------------|
| CLAUDE.md | ~/.claude/CLAUDE.md | ./CLAUDE.md |
| Settings | ~/.claude/settings.json | - |
| Commands | ~/.claude/commands/ | ./.claude/commands/ |
| Skills | ~/.claude/skills/ | - |
| Hooks | ~/.claude/hooks/ | - |
| Rules | - | ./.claude/rules/ |

---

## Installation Commands

### Quick Install (Global)
```bash
# 1. Extract engineer package
cd /tmp/claudekit-analysis/claudekit-engineer-main
cp -r .claude/* ~/.claude/

# 2. Install Python dependencies for skills
cd ~/.claude/skills && chmod +x install.sh && ./install.sh

# 3. Verify installation
ls -la ~/.claude/
```

### Project Setup
```bash
# 1. Copy project-specific files
cp /tmp/claudekit-analysis/claudekit-engineer-main/CLAUDE.md /root/repo/terragon-oss/

# 2. Create project .claude directory
mkdir -p /root/repo/terragon-oss/.claude/commands
mkdir -p /root/repo/terragon-oss/.claude/rules

# 3. Copy rules
cp -r /tmp/claudekit-analysis/claudekit-engineer-main/.claude/rules/* \
      /root/repo/terragon-oss/.claude/rules/
```

---

## Testing the Installation

1. **Verify hooks**: `ls ~/.claude/hooks/`
2. **Test command**: Run `/ck-help` in Claude Code
3. **Test skill**: Activate a skill in conversation
4. **Test agent**: Delegate to an agent

---

## Recommendations Summary

| Priority | Action | Effort |
|----------|--------|--------|
| **High** | Install Engineer package globally | 5 min |
| **High** | Configure privacy/scout hooks | 10 min |
| **Medium** | Create terragon-oss CLAUDE.md | 15 min |
| **Medium** | Add project-specific commands | 30 min |
| **Low** | Install Marketing skills | 5 min |
| **Low** | Customize statusline | 15 min |

---

## Next Steps

1. **Immediate**: Install ClaudeKit Engineer globally
2. **Today**: Configure hooks and verify functionality
3. **This Week**: Create terragon-oss specific customizations
4. **Ongoing**: Develop custom skills as needed
