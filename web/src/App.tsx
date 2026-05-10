import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { OverviewPage } from './pages/OverviewPage';
import { PriorityQueuePage } from './pages/PriorityQueuePage';
import { ClinicsPage } from './pages/ClinicsPage';
import { ClinicDetailPage } from './pages/ClinicDetailPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/priority-queue" element={<PriorityQueuePage />} />
          <Route path="/clinics" element={<ClinicsPage />} />
          <Route path="/clinics/:id" element={<ClinicDetailPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
