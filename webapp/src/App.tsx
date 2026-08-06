import { useEffect } from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import Dashboard from "./screens/Dashboard";
import PromiseList from "./screens/PromiseList";
import PromiseDetail from "./screens/PromiseDetail";
import NewPromise from "./screens/NewPromise";
import Profile from "./screens/Profile";
import { ThemeProvider } from "./lib/useTheme.tsx";

export default function App() {
  const location = useLocation();

  // RTL page transitions via AnimatePresence (mode="wait")
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  return (
    <ThemeProvider>
      <div className="mx-auto min-h-screen max-w-md px-4 pb-28 pt-6">
        <AnimatePresence mode="wait">
          <Routes location={location} key={location.pathname}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/promises/:type" element={<PromiseList />} />
            <Route path="/promise/:id" element={<PromiseDetail />} />
            <Route path="/new" element={<NewPromise />} />
            <Route path="/profile" element={<Profile />} />
          </Routes>
        </AnimatePresence>
      </div>
    </ThemeProvider>
  );
}
