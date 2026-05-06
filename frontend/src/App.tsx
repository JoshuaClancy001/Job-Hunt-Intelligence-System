import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { NewJobs } from "./pages/Jobs";
import { SavedJobs } from "./pages/SavedJobs";
import { Applications } from "./pages/Applications";
import { Insights } from "./pages/Insights";
import { Profile } from "./pages/Profile";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/jobs" element={<NewJobs />} />
          <Route path="/saved" element={<SavedJobs />} />
          <Route path="/applications" element={<Applications />} />
          <Route path="/insights" element={<Insights />} />
          <Route path="/profile" element={<Profile />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
