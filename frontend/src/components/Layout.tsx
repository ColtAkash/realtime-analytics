import { Outlet } from "react-router-dom";
import ConnectionStatus from "./ConnectionStatus";
import DarkModeToggle from "./DarkModeToggle";

export default function Layout() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 backdrop-blur bg-surface-light/80 dark:bg-surface-dark/80 border-b border-slate-200 dark:border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold tracking-tight">
              Realtime Analytics
            </h1>
          </div>
          <div className="flex items-center gap-4">
            <ConnectionStatus />
            <DarkModeToggle />
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        <Outlet />
      </main>
    </div>
  );
}
