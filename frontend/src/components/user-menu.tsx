"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { LogOut, Settings, LayoutDashboard, User, ChevronDown } from "lucide-react";
import { useAuthStore } from "@/store/auth-store";
import { useAuth } from "@/hooks/useAuth";

export function UserMenu() {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { user } = useAuthStore();
  const { logout } = useAuth();

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const initials = user?.full_name
    ? user.full_name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
    : user?.username?.slice(0, 2).toUpperCase() ?? "?";

  function navigate(path: string) {
    setOpen(false);
    router.push(path);
  }

  return (
    <div className="relative flex items-center gap-3" ref={menuRef}>
      {/* Sync Status — placeholder for future badge */}
      <div className="hidden sm:flex items-center gap-1.5 text-xs text-muted-foreground bg-muted px-2.5 py-1 rounded-full">
        <span className="w-1.5 h-1.5 rounded-full bg-green-500 inline-block" />
        Synced
      </div>

      {/* Profile button */}
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 rounded-full pl-1 pr-2 py-1 hover:bg-muted transition-colors focus:outline-none focus:ring-2 focus:ring-ring"
        aria-label="Open profile menu"
        aria-expanded={open}
      >
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground text-sm font-semibold select-none">
          {initials}
        </div>
        <ChevronDown className={`h-3.5 w-3.5 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute right-0 top-full mt-2 w-56 rounded-lg border bg-popover shadow-lg z-50 overflow-hidden animate-in fade-in-0 zoom-in-95">
          {/* User info header */}
          <div className="px-4 py-3 border-b bg-muted/30">
            <p className="text-sm font-semibold truncate">{user?.full_name ?? user?.username ?? "User"}</p>
            <p className="text-xs text-muted-foreground truncate mt-0.5">
              {user?.gmail_email ?? "No Gmail connected"}
            </p>
          </div>

          {/* Menu items */}
          <div className="py-1">
            <button
              onClick={() => navigate("/dashboard")}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-muted transition-colors text-left"
            >
              <LayoutDashboard className="h-4 w-4 text-muted-foreground" />
              Dashboard
            </button>
            <button
              onClick={() => navigate("/settings")}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-muted transition-colors text-left"
            >
              <Settings className="h-4 w-4 text-muted-foreground" />
              Settings
            </button>
          </div>

          <div className="border-t py-1">
            <button
              onClick={() => { setOpen(false); logout(); }}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-destructive hover:bg-destructive/10 transition-colors text-left"
            >
              <LogOut className="h-4 w-4" />
              Sign Out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
