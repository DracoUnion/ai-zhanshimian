import { Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import LandingPage from './pages/LandingPage';
import WorkspacePage from './pages/WorkspacePage';
import ResultPage from './pages/ResultPage';
import PricingPage from './pages/PricingPage';
import AccountPage from './pages/AccountPage';
import HistoryPage from './pages/HistoryPage';

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/workspace" element={<WorkspacePage />} />
        <Route path="/result/:id" element={<ResultPage />} />
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="/account" element={<AccountPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="*" element={<LandingPage />} />
      </Routes>
    </Layout>
  );
}