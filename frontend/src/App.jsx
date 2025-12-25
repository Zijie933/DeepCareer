import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import Crawler from './pages/Crawler'
import Jobs from './pages/Jobs'
import Resume from './pages/Resume'
import Match from './pages/Match'
import SmartMatch from './pages/SmartMatch'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="crawler" element={<Crawler />} />
        <Route path="jobs" element={<Jobs />} />
        <Route path="resume" element={<Resume />} />
        <Route path="match" element={<Match />} />
        <Route path="smart-match" element={<SmartMatch />} />
      </Route>
    </Routes>
  )
}
