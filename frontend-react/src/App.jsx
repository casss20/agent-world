import { Routes, Route } from 'react-router-dom'
import { LedgerProvider } from './providers/LedgerProvider'
import { ApprovalProvider } from './providers/ApprovalProvider'
import { BusinessProvider } from './providers/BusinessProvider'
import { LedgerShell } from './components/shell/LedgerShell'
import { GlobalHQ } from './pages/GlobalHQ'
import { BusinessWorkspace } from './components/businesses/BusinessWorkspace'

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
            <Route path="/" element={<GlobalHQ />} />
            <Route path="/hq" element={<GlobalHQ />} />
            <Route path="/business/:id" element={<BusinessRouteWrapper />} />
            <Route path="/business/:id/*" element={<BusinessRouteWrapper />} />
          </Routes>
        </LedgerShell>
      </ApprovalProvider>
    </LedgerProvider>
  );
}

// Wrapper to extract businessId from URL
import { useParams } from 'react-router-dom'

function BusinessRouteWrapper() {
  const { id } = useParams()
  return <BusinessRoute businessId={id} />
}

export default App
