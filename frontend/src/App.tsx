import { NavLink, Route, Routes } from "react-router-dom";
import { AppControls } from "@/components/AppControls";
import ChatPage from "@/pages/ChatPage";
import ConfigPage from "@/pages/ConfigPage";
import { cn } from "@/utils";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    "px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
    isActive
      ? "bg-primary text-primary-foreground"
      : "text-muted-foreground hover:text-foreground hover:bg-muted",
  );

export default function App() {
  return (
    <div className="flex h-screen flex-col bg-background text-foreground font-sans antialiased">
      <header className="shrink-0 border-b border-border bg-muted/30">
        <div className="flex items-center justify-between gap-4 px-4 py-2 pr-44 sm:pr-52">
          <div className="flex items-center gap-4">
            <span className="font-semibold text-sm sm:text-base whitespace-nowrap">
              Knowledge HUB
            </span>
            <nav className="flex items-center gap-1">
              <NavLink to="/" end className={navLinkClass}>
                Chat
              </NavLink>
              <NavLink to="/config" className={navLinkClass}>
                Configuration
              </NavLink>
            </nav>
          </div>
        </div>
      </header>

      <AppControls />

      <div className="flex-1 min-h-0 overflow-hidden">
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/config" element={<ConfigPage />} />
        </Routes>
      </div>
    </div>
  );
}
