import { useLocation, useNavigate } from 'react-router'

import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'

export function DashboardModeTabs() {
  const location = useLocation()
  const navigate = useNavigate()
  const value = location.pathname.startsWith('/battle') ? 'battle' : 'training'

  return (
    <Tabs value={value} onValueChange={(next) => navigate(next === 'battle' ? '/battle' : '/')}>
      <TabsList aria-label="dashboard mode" className="dashboard-mode-tabs">
        <TabsTrigger value="training">Training</TabsTrigger>
        <TabsTrigger value="battle">Battle</TabsTrigger>
      </TabsList>
    </Tabs>
  )
}
