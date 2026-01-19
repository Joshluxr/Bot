'use client';

import { useState, useEffect, useCallback } from 'react';
import { DashboardHeader } from '@/components/dashboard/header';
import { TaskList } from '@/components/dashboard/task-list';
import { TaskDetail } from '@/components/dashboard/task-detail';
import { NewTaskDialog } from '@/components/dashboard/new-task-dialog';
import { Sidebar } from '@/components/dashboard/sidebar';

export interface Task {
  id: string;
  title: string;
  status: 'running' | 'queued' | 'completed' | 'failed' | 'pending' | 'cancelled';
  progress?: number;
  repository: { fullName: string; owner: string; name: string };
  branch: string;
  agent: string;
  prUrl?: string;
  error?: string;
  createdAt: string;
  updatedAt: string;
}

interface TasksResponse {
  success: boolean;
  data: {
    items: Task[];
    total: number;
    page: number;
    pageSize: number;
    hasMore: boolean;
  };
}

async function fetchTasks(status?: string): Promise<Task[]> {
  try {
    const params = new URLSearchParams();
    if (status && status !== 'all') {
      params.set('status', status.toUpperCase());
    }
    params.set('pageSize', '50');

    const response = await fetch(`/api/tasks?${params.toString()}`, {
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error('Failed to fetch tasks');
    }

    const data: TasksResponse = await response.json();

    // Transform API response to match component interface
    return data.data.items.map((item) => ({
      ...item,
      status: item.status.toLowerCase() as Task['status'],
      repository: {
        fullName: item.repository?.fullName || '',
        owner: item.repository?.owner || '',
        name: item.repository?.name || '',
      },
      agent: item.agent || 'claude',
    }));
  } catch (error) {
    console.error('Error fetching tasks:', error);
    return [];
  }
}

export default function DashboardPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [isNewTaskOpen, setIsNewTaskOpen] = useState(false);
  const [filter, setFilter] = useState<'all' | 'running' | 'queued' | 'completed' | 'failed'>('all');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const loadTasks = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const fetchedTasks = await fetchTasks();
      setTasks(fetchedTasks);
    } catch (err) {
      setError('Failed to load tasks. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTasks();

    // Poll for updates every 10 seconds for running tasks
    const interval = setInterval(() => {
      loadTasks();
    }, 10000);

    return () => clearInterval(interval);
  }, [loadTasks]);

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
          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 rounded-lg bg-red-500/10 text-red-500 text-sm">
              {error}
              <button
                onClick={loadTasks}
                className="ml-4 underline hover:no-underline"
              >
                Retry
              </button>
            </div>
          )}

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

          {/* Loading State */}
          {isLoading && tasks.length === 0 && (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" />
            </div>
          )}

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
