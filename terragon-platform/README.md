# Terragon Platform

> Delegate coding tasks to AI background agents. Get pull requests, not promises.

Terragon is an AI-powered development automation platform that runs coding agents in isolated cloud sandboxes to complete your tasks autonomously.

## Features

- **AI Coding Agents**: Choose from Claude Code, GPT-4, Gemini, or bring your own
- **Isolated Sandboxes**: Each task runs in its own secure cloud environment
- **Automatic PRs**: Changes are committed and PRs created automatically
- **Real-time Logs**: Watch your agent work in real-time
- **Multiple Integrations**: GitHub, Slack, Linear, and webhooks
- **Task Scheduling**: Queue tasks and run automations

## Architecture

```
terragon-platform/
├── apps/
│   ├── web/          # Next.js frontend
│   ├── api/          # Express API server
│   └── worker/       # Background job worker
├── packages/
│   ├── database/     # Prisma schema and client
│   ├── shared/       # Shared types and utilities
│   └── ui/           # React component library
└── docker-compose.yml
```

## Tech Stack

- **Frontend**: Next.js 14, React 18, Tailwind CSS, shadcn/ui
- **Backend**: Express.js, Socket.io, BullMQ
- **Database**: PostgreSQL, Prisma ORM
- **Cache/Queue**: Redis
- **Auth**: NextAuth.js (GitHub OAuth)
- **Payments**: Stripe

## Getting Started

### Prerequisites

- Node.js 18+
- pnpm 8+
- Docker & Docker Compose
- GitHub OAuth App
- Stripe Account (for billing)

### Setup

1. **Clone and install dependencies**:

```bash
git clone https://github.com/your-org/terragon-platform.git
cd terragon-platform
pnpm install
```

2. **Set up environment variables**:

```bash
cp .env.example .env
# Edit .env with your credentials
```

3. **Start the database and Redis**:

```bash
docker-compose up -d postgres redis
```

4. **Set up the database**:

```bash
pnpm db:generate
pnpm db:push
```

5. **Start the development servers**:

```bash
pnpm dev
```

This will start:
- Web: http://localhost:3000
- API: http://localhost:4000

### Production Deployment

Using Docker:

```bash
docker-compose up -d
```

Or deploy to:
- **Frontend**: Vercel
- **API/Worker**: Railway, Render, or Fly.io
- **Database**: Supabase, Neon, or managed PostgreSQL
- **Redis**: Upstash or managed Redis

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `JWT_SECRET` | Secret for JWT signing |
| `GITHUB_CLIENT_ID` | GitHub OAuth app ID |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth secret |
| `STRIPE_SECRET_KEY` | Stripe secret key |
| `ANTHROPIC_API_KEY` | API key for Claude |
| `OPENAI_API_KEY` | API key for GPT-4 |

## API Endpoints

### Authentication
- `POST /api/auth/github/callback` - GitHub OAuth callback
- `GET /api/auth/me` - Get current user

### Tasks
- `GET /api/tasks` - List tasks
- `POST /api/tasks` - Create task
- `GET /api/tasks/:id` - Get task details
- `POST /api/tasks/:id/cancel` - Cancel task

### Integrations
- `GET /api/integrations` - List integrations
- `GET /api/integrations/github/repos` - List GitHub repos
- `POST /api/integrations/slack` - Connect Slack

### Billing
- `GET /api/billing/subscription` - Get subscription
- `POST /api/billing/checkout` - Create checkout session
- `POST /api/billing/portal` - Create billing portal session

## WebSocket Events

Connect to the API server with Socket.io:

```javascript
const socket = io('http://localhost:4000', {
  auth: { token: 'your-jwt-token' }
});

socket.on('task:started', (data) => { ... });
socket.on('task:progress', (data) => { ... });
socket.on('task:completed', (data) => { ... });
socket.on('task:failed', (data) => { ... });
socket.on('log', (data) => { ... });
```

## License

MIT
