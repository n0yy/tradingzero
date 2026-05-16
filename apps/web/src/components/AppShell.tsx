import type { ComponentType } from 'react'
import { NavLink, Outlet } from 'react-router'
import { Bot, Gauge, ListChecks, Map, Settings2, ShieldAlert, Timer } from 'lucide-react'

import { cn } from '@/lib/utils'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarInset,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  SidebarSeparator,
  SidebarTrigger,
} from '@/components/ui/sidebar'
import { useUIStore } from '@/store/ui'

const navItems: { to: string; label: string; end?: boolean; icon: ComponentType<{ className?: string }> }[] = [
  { to: '/', label: 'Live View', end: true, icon: Gauge },
  { to: '/battle', label: 'Battle', icon: Bot },
  { to: '/config', label: 'Config', icon: Settings2 },
  { to: '/runs', label: 'Runs', icon: ListChecks },
  { to: '/errors', label: 'Errors', icon: ShieldAlert },
  { to: '/roadmap', label: 'Roadmap', icon: Map },
]

export function AppShell() {
  const timeMode = useUIStore((s) => s.timeMode)
  const toggleTimeMode = useUIStore((s) => s.toggleTimeMode)

  return (
    <SidebarProvider defaultOpen>
      <Sidebar collapsible="icon" variant="sidebar">
        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel className="font-display text-base tracking-wide text-primary">
              TradingZero
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <nav aria-label="primary">
                <SidebarMenu>
                  {navItems.map((item) => (
                    <SidebarMenuItem key={item.to}>
                      <NavLink to={item.to} end={item.end}>
                        {({ isActive }) => (
                          <SidebarMenuButton asChild isActive={isActive} tooltip={item.label}>
                            <span>
                              <item.icon className="size-4" />
                              <span>{item.label}</span>
                            </span>
                          </SidebarMenuButton>
                        )}
                      </NavLink>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </nav>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>
        <SidebarSeparator />
        <SidebarFooter>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton
                onClick={toggleTimeMode}
                tooltip={`Time mode: ${timeMode.toUpperCase()}`}
                className="w-full"
              >
                <Timer className="size-4" />
                <span>Time</span>
              </SidebarMenuButton>
              <SidebarMenuBadge>{timeMode.toUpperCase()}</SidebarMenuBadge>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarFooter>
        <SidebarRail />
      </Sidebar>
      <SidebarInset>
        <div className="flex h-12 items-center gap-2 border-b border-border/70 px-3">
          <SidebarTrigger data-testid="sidebar-trigger" />
          <span className="font-display text-sm tracking-wide text-muted-foreground">TradingZero</span>
          <Settings2 className="ml-auto size-4 text-muted-foreground" aria-hidden="true" />
        </div>
        <div className={cn('min-w-0 flex-1')}>
          <Outlet />
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
