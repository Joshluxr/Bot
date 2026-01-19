'use client';

import Link from 'next/link';
import { Leaf, Menu, Plus, Bell, User } from 'lucide-react';

interface DashboardHeaderProps {
  onMenuClick?: () => void;
  onNewTask?: () => void;
}

export function DashboardHeader({ onMenuClick, onNewTask }: DashboardHeaderProps) {
  return (
    <header className="sticky top-0 z-30 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center px-4 md:px-6">
        {/* Mobile Menu Button */}
        <button
          onClick={onMenuClick}
          className="mr-4 p-2 -ml-2 rounded-lg hover:bg-muted lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* Logo (mobile only) */}
        <Link href="/" className="flex items-center gap-2 lg:hidden">
          <Leaf className="h-5 w-5 text-primary" />
          <span className="font-semibold">Terragon</span>
        </Link>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Actions */}
        <div className="flex items-center gap-2">
          {/* New Task Button */}
          <button
            onClick={onNewTask}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg font-medium text-sm hover:bg-primary/90 transition-colors"
          >
            <Plus className="h-4 w-4" />
            <span className="hidden sm:inline">New Task</span>
          </button>

          {/* Notifications */}
          <button className="p-2 rounded-lg hover:bg-muted relative">
            <Bell className="h-5 w-5" />
            <span className="absolute top-1.5 right-1.5 h-2 w-2 bg-primary rounded-full" />
          </button>

          {/* User Menu */}
          <button className="p-2 rounded-lg hover:bg-muted">
            <User className="h-5 w-5" />
          </button>
        </div>
      </div>
    </header>
  );
}
