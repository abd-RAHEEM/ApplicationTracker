"use client";

import { LogOut, Settings, User } from "lucide-react";

export function UserMenu() {
  return (
    <div className="flex items-center gap-4">
      {/* Sync Status Badge goes here */}
      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary">
        <User className="h-4 w-4" />
      </div>
    </div>
  );
}
