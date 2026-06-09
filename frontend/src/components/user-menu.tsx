"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { LogOut, Settings, LayoutDashboard, ChevronDown, RefreshCw, Wifi, WifiOff } from "lucide-react";
import { useAuthStore } from "@/store/auth-store";
import { useAuth } from "@/hooks/useAuth";
import { apiClient, getApiError } from "@/lib/api-client";
import { toast } from "sonner";

const SYNC_KEY = "last_sync_at"; // localStorage key for last sync timestamp

function getLastSyncTime(): Date | null {
  if (typeof window === "undefined") return null;
  const val = localStorage.getItem(SYNC_KEY);
  if (!val) return null;
  const d = new Date(val);
  return isNaN(d.getTime()) ? null : d;
}

function formatSyncTime(date: Date | null): string {
  if (!date) return "Never synced";
  const diff = Date.now() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  if (days > 0) return `${days}d ago`;
  if (hours > 0) return `${hours}h ago`;
  if (minutes > 0) return `${minutes}m ago`;
  return "Just now";
}

function isSynced(date: Date | null): boolean {
  if (!date) return false;
  const diff = Date.now() - date.getTime();
  return diff < 60 * 60 * 1000; // Synced within last hour
}

export function UserMenu() {
  const [open, setOpen] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSync, setLastSync] = useState<Date | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { user } = useAuthStore();
  const { logout } = useAuth();

  // Load last sync time from localStorage on mount
  useEffect(() => {
    setLastSync(getLastSyncTime());
    // Update every minute to keep "X minutes ago" fresh
    const interval = setInterval(() => {
      setLastSync(getLastSyncTime());
    }, 60 * 1000);
    return () => clearInterval(interval);
  }, []);

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

  async function handleSync() {
    if (isSyncing || !user?.gmail_connected) return;
    setIsSyncing(true);
    try {
      await apiClient.post("/sync/now");
      const now = new Date();
      localStorage.setItem(SYNC_KEY, now.toISOString());
      setLastSync(now);
      toast.success("Sync started! Your applications will update shortly.");
    } catch (error: unknown) {
      const apiError = getApiError(error);
      toast.error(apiError.message || "Sync failed. Please try again.");
    } finally {
      setIsSyncing(false);
    }
  }

  const synced = isSynced(lastSync);
  const syncLabel = formatSyncTime(lastSync);
  const gmailConnected = user?.gmail_connected ?? false;

  return (
    <div className="relative flex items-center gap-3" ref={menuRef}>
      {/* Sync Status Button */}
      <button
        id="sync-button"
        onClick={handleSync}
        disabled={isSyncing || !gmailConnected}
        title={
          !gmailConnected
            ? "Connect Gmail to enable sync"
            : isSyncing
            ? "Syncing..."
            : `Last synced: ${syncLabel}. Click to sync now.`
        }
        className={`
          hidden sm:flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border transition-all
          ${isSyncing ? "opacity-70 cursor-not-allowed" : "cursor-pointer hover:shadow-sm"}
          ${
            !gmailConnected
              ? "bg-muted text-muted-foreground border-transparent"
              : synced
              ? "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-400 dark:border-green-800 hover:bg-green-100"
              : "bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-900/20 dark:text-orange-400 dark:border-orange-800 hover:bg-orange-100"
          }
        `}
      >
        {isSyncing ? (
          <>
            <RefreshCw className="w-3 h-3 animate-spin" />
            <span>Syncing...</span>
          </>
        ) : !gmailConnected ? (
          <>
            <WifiOff className="w-3 h-3" />
            <span>No Gmail</span>
          </>
        ) : synced ? (
          <>
            <Wifi className="w-3 h-3" />
            <span>Synced {syncLabel}</span>
          </>
        ) : (
          <>
            <RefreshCw className="w-3 h-3" />
            <span>{lastSync ? `Sync (${syncLabel})` : "Sync now"}</span>
          </>
        )}
      </button>

      {/* Profile button */}
      <button
        id="user-menu-button"
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
              id="nav-dashboard"
              onClick={() => navigate("/dashboard")}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-muted transition-colors text-left"
            >
              <LayoutDashboard className="h-4 w-4 text-muted-foreground" />
              Dashboard
            </button>
            <button
              id="nav-settings"
              onClick={() => navigate("/settings")}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-muted transition-colors text-left"
            >
              <Settings className="h-4 w-4 text-muted-foreground" />
              Settings
            </button>
          </div>

          <div className="border-t py-1">
            <button
              id="sign-out-button"
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
