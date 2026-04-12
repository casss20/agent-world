import { Routes, Route } from 'react-router-dom'
import LedgerHQ from './pages/LedgerHQ'

function App() {
  return (
    <Routes>
      <Route path="/" element={<LedgerHQ />} />
      <Route path="/ledger" element={<LedgerHQ />} />
    </Routes>
  )
}

export default App
