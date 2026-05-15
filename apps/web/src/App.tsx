import { Route, Routes } from 'react-router'

import './App.css'
import { AppShell } from './components/AppShell'
import BattlePage from './routes/BattlePage'
import ConfigPage from './routes/ConfigPage'
import ErrorsPage from './routes/ErrorsPage'
import LiveView from './routes/LiveView'
import RunsPage from './routes/RunsPage'

function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<LiveView />} />
        <Route path="battle" element={<BattlePage />} />
        <Route path="config" element={<ConfigPage />} />
        <Route path="runs" element={<RunsPage />} />
        <Route path="errors" element={<ErrorsPage />} />
      </Route>
    </Routes>
  )
}

export default App
