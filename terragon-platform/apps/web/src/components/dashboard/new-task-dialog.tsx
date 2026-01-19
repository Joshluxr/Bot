'use client';

import { useState } from 'react';
import { X, GitBranch, Bot, ChevronDown } from 'lucide-react';

interface NewTaskDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

const agents = [
  { id: 'claude', name: 'Claude Code', description: 'Anthropic' },
  { id: 'openai', name: 'OpenAI Codex', description: 'OpenAI' },
  { id: 'gemini', name: 'Gemini', description: 'Google' },
  { id: 'amp', name: 'Amp', description: 'Sourcegraph' },
  { id: 'opencode', name: 'OpenCode', description: 'Open Source' },
];

const mockRepos = [
  { id: '1', fullName: 'acme/frontend', defaultBranch: 'main' },
  { id: '2', fullName: 'acme/backend', defaultBranch: 'main' },
  { id: '3', fullName: 'acme/mobile', defaultBranch: 'develop' },
];

export function NewTaskDialog({ isOpen, onClose }: NewTaskDialogProps) {
  const [repository, setRepository] = useState('');
  const [branch, setBranch] = useState('main');
  const [agent, setAgent] = useState('claude');
  const [prompt, setPrompt] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000));

    setIsSubmitting(false);
    onClose();

    // Reset form
    setRepository('');
    setBranch('main');
    setAgent('claude');
    setPrompt('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Dialog */}
      <div className="relative w-full max-w-lg mx-4 bg-card rounded-xl shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">New Task</h2>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-muted"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {/* Repository */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Repository
            </label>
            <div className="relative">
              <GitBranch className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <select
                value={repository}
                onChange={(e) => setRepository(e.target.value)}
                required
                className="w-full pl-10 pr-10 py-2 rounded-lg border bg-background appearance-none focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">Select a repository</option>
                {mockRepos.map((repo) => (
                  <option key={repo.id} value={repo.fullName}>
                    {repo.fullName}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
            </div>
          </div>

          {/* Branch */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Base Branch
            </label>
            <input
              type="text"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              placeholder="main"
              className="w-full px-3 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {/* Agent */}
          <div>
            <label className="block text-sm font-medium mb-2">
              AI Agent
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {agents.map((a) => (
                <button
                  key={a.id}
                  type="button"
                  onClick={() => setAgent(a.id)}
                  className={`flex flex-col items-start p-3 rounded-lg border text-left transition-colors ${
                    agent === a.id
                      ? 'border-primary bg-primary/5'
                      : 'hover:bg-muted'
                  }`}
                >
                  <span className="text-sm font-medium">{a.name}</span>
                  <span className="text-xs text-muted-foreground">{a.description}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Prompt */}
          <div>
            <label className="block text-sm font-medium mb-2">
              What would you like the agent to do?
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              required
              rows={4}
              placeholder="Describe your task in detail..."
              className="w-full px-3 py-2 rounded-lg border bg-background resize-none focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Be specific about what you want. The agent will analyze your codebase and implement the task.
            </p>
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 px-4 border rounded-lg font-medium text-sm hover:bg-muted transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !repository || !prompt}
              className="flex-1 py-2 px-4 bg-primary text-primary-foreground rounded-lg font-medium text-sm hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Creating...' : 'Create Task'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
