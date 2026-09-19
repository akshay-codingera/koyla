import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { AuditLog } from './pages/AuditLog';
import { DocumentList } from './pages/DocumentList';
import { DocumentDetail } from './pages/DocumentDetail';
import { DocumentUpload } from './pages/DocumentUpload';
import { VerificationQueue } from './pages/VerificationQueue';
import { KnowledgeExplorer } from './pages/KnowledgeExplorer';
import { AIQuery } from './pages/AIQuery';
import { ReportList } from './pages/ReportList';
import { ReportNew } from './pages/ReportNew';
import { ReportStudio } from './pages/ReportStudio';
import { TopicIntelligence } from './pages/TopicIntelligence';
import { SystemStatus } from './pages/SystemStatus';
import { ProtectedRoute } from './components/ProtectedRoute';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<ProtectedRoute />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="query" element={<AIQuery />} />
          <Route path="ask" element={<AIQuery />} />
          <Route path="knowledge" element={<KnowledgeExplorer />} />
          <Route path="search" element={<KnowledgeExplorer />} />
          <Route path="reports" element={<ReportList />} />
          <Route path="reports/new" element={<ReportNew />} />
          <Route path="reports/:id" element={<ReportStudio />} />
          <Route path="topics" element={<TopicIntelligence />} />
          <Route path="documents" element={<DocumentList />} />
          <Route path="documents/:id" element={<DocumentDetail />} />
          <Route path="verification" element={<VerificationQueue />} />
          <Route path="upload" element={<DocumentUpload />} />
          <Route path="governance" element={<AuditLog />} />
          <Route path="audit" element={<AuditLog />} />
          <Route path="system" element={<SystemStatus />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App;
