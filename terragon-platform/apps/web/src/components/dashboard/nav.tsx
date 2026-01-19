'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@terragon/ui';
import {
  LayoutDashboard,
  ListTodo,
  Plug,
  Settings,
  CreditCard,
  Zap,
  Key,
} from 'lucide-react';

const navItems = [
  {
    title: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    title: 'Tasks',
    href: '/dashboard/tasks',
    icon: ListTodo,
  },
  {
    title: 'Automations',
    href: '/dashboard/automations',
    icon: Zap,
  },
  {
    title: 'Integrations',
    href: '/dashboard/integrations',
    icon: Plug,
  },
  {
    title: 'API Keys',
    href: '/dashboard/api-keys',
    icon: Key,
  },
  {
    title: 'Billing',
    href: '/dashboard/billing',
    icon: CreditCard,
  },
  {
    title: 'Settings',
    href: '/dashboard/settings',
    icon: Settings,
  },
];

export function DashboardNav() {
  const pathname = usePathname();

  return (
    <nav className="hidden lg:flex w-64 flex-col border-r bg-muted/30 min-h-[calc(100vh-4rem)]">
      <div className="flex-1 py-4">
        <div className="px-3 py-2">
          <div className="space-y-1">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  pathname === item.href
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.title}
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Credits display */}
      <div className="p-4 border-t">
        <div className="rounded-lg bg-card p-4">
          <p className="text-sm font-medium">Credits</p>
          <p className="text-2xl font-bold">847</p>
          <p className="text-xs text-muted-foreground">of 1,000 this month</p>
          <div className="mt-2 h-2 rounded-full bg-muted overflow-hidden">
            <div className="h-full w-[85%] bg-primary rounded-full" />
          </div>
        </div>
      </div>
    </nav>
  );
}
