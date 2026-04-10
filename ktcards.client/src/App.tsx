import { BrowserRouter, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import AdminPage from './pages/AdminPage';
import TeamCardsPage from './pages/TeamCardsPage';

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/admin" element={<AdminPage />} />
                <Route path="/teams/:teamId" element={<TeamCardsPage />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;