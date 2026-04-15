import { Routes, Route } from 'react-router-dom'
import { useParams } from 'react-router-dom'
import { LedgerProvider } from './providers/LedgerProvider'
import { ApprovalProvider } from './providers/ApprovalProvider'
import { BusinessProvider } from './providers/BusinessProvider'
import { LedgerShell } from './components/shell/LedgerShell'
import { GlobalHQ } from './pages/GlobalHQ'
import { BusinessWorkspace } from './components/businesses/BusinessWorkspace'
import SpawnPage from './pages/SpawnPage'
import { AuditLogViewer } from './components/audit/AuditLogViewer'
import { ApprovalGate } from './components/governance/ApprovalGate'
import ChannelsPage from './pages/ChannelsPage'
import AgentTemplatesPage from './pages/AgentTemplatesPage'

// Business Workspace Wrapper
function BusinessRoute({ businessId }) {
  return (
    <BusinessProvider businessId={businessId}>
      <BusinessWorkspace />
    </BusinessProvider>
  );
}

function App() {
  return (
    <LedgerProvider>
      <ApprovalProvider>
        <LedgerShell>
          <Routes>
            <Route path="/"             element={<GlobalHQ />} />
            <Route path="/hq"           element={<GlobalHQ />} />
            <Route path="/spawn"        element={<SpawnPage />} />
            <Route path="/audit"        element={<AuditLogViewer />} />
            <Route path="/approvals"    element={<ApprovalGate />} />
            <Route path="/channels"     element={<ChannelsPage />} />
            <Route path="/agents"       element={<AgentTemplatesPage />} />
            <Route path="/business/:id"   element={<BusinessRouteWrapper />} />
            <Route path="/business/:id/*" element={<BusinessRouteWrapper />} />
          </Routes>
        </LedgerShell>
      </ApprovalProvider>
    </LedgerProvider>
  );
}


function BusinessRouteWrapper() {
  const { id } = useParams()
  return <BusinessRoute businessId={id} />
}

export default App


