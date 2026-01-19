'use client';

import { useState } from 'react';
import { DashboardHeader } from '@/components/dashboard/header';
import { TaskList } from '@/components/dashboard/task-list';
import { TaskDetail } from '@/components/dashboard/task-detail';
import { NewTaskDialog } from '@/components/dashboard/new-task-dialog';
import { Sidebar } from '@/components/dashboard/sidebar';

// Mock data for demonstration
const mockTasks = [
  {
    id: 'task_abc123',
    title: 'Add authentication flow',
    status: 'running' as const,
    progress: 75,
    repository: { fullName: 'acme/frontend', owner: 'acme', name: 'frontend' },
    branch: 'feat/auth-flow',
    agent: 'claude',
    createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
  },
  {
    id: 'task_def456',
    title: 'Fix pagination bug',
    status: 'queued' as const,
    repository: { fullName: 'acme/frontend', owner: 'acme', name: 'frontend' },
    branch: 'fix/pagination',
    agent: 'openai',
    createdAt: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 'task_ghi789',
    title: 'Refactor API endpoints',
    status: 'completed' as const,
    progress: 100,
    prUrl: 'https://github.com/acme/backend/pull/42',
    repository: { fullName: 'acme/backend', owner: 'acme', name: 'backend' },
    branch: 'refactor/api',
    agent: 'claude',
    createdAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(Date.now() - 20 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 'task_jkl012',
    title: 'Add unit tests for utils',
    status: 'failed' as const,
    repository: { fullName: 'acme/frontend', owner: 'acme', name: 'frontend' },
    branch: 'test/utils',
    agent: 'gemini',
    error: 'Test suite failed with 3 errors',
    createdAt: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(Date.now() - 2.5 * 60 * 60 * 1000).toISOString(),
  },
];

export type Task = (typeof mockTasks)[0];

export default function DashboardPage() {
  const [tasks] = useState(mockTasks);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [isNewTaskOpen, setIsNewTaskOpen] = useState(false);
  const [filter, setFilter] = useState<'all' | 'running' | 'queued' | 'completed' | 'failed'>('all');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const selectedTask = tasks.find((t) => t.id === selectedTaskId);

  const filteredTasks = filter === 'all'
    ? tasks
    : tasks.filter((t) => t.status === filter);

  return (
    <div className="min-h-screen bg-background flex">
      {/* Mobile Sidebar Overlay */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-h-screen lg:pl-64">
        <DashboardHeader
          onMenuClick={() => setIsSidebarOpen(true)}
          onNewTask={() => setIsNewTaskOpen(true)}
        />

        <main className="flex-1 p-4 md:p-6">
          {/* Filter Tabs */}
          <div className="flex gap-2 mb-6 overflow-x-auto pb-2 -mx-4 px-4 md:mx-0 md:px-0">
            {(['all', 'running', 'queued', 'completed', 'failed'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                  filter === f
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted hover:bg-muted/80'
                }`}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
                {f !== 'all' && (
                  <span className="ml-2 text-xs opacity-70">
                    {tasks.filter((t) => t.status === f).length}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Task Grid / List */}
          <div className="grid gap-6 lg:grid-cols-2">
            <div className={`${selectedTask ? 'hidden lg:block' : ''}`}>
              <TaskList
                tasks={filteredTasks}
                selectedId={selectedTaskId}
                onSelect={setSelectedTaskId}
              />
            </div>

            {selectedTask && (
              <div className="lg:col-span-1">
                <TaskDetail
                  task={selectedTask}
                  onClose={() => setSelectedTaskId(null)}
                />
              </div>
            )}

            {!selectedTask && (
              <div className="hidden lg:flex items-center justify-center rounded-xl border bg-card p-12 text-center">
                <div>
                  <p className="text-muted-foreground mb-2">Select a task to view details</p>
                  <p className="text-sm text-muted-foreground">
                    Or create a new task to get started
                  </p>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>

      {/* New Task Dialog */}
      <NewTaskDialog
        isOpen={isNewTaskOpen}
        onClose={() => setIsNewTaskOpen(false)}
      />
    </div>
  );
}
