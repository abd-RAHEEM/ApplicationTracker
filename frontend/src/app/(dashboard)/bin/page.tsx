"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RefreshCw, Trash2 } from "lucide-react";

export default function BinPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Bin</h2>
        <p className="text-muted-foreground">Applications here will be permanently deleted after 15 days.</p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="rounded-md border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50 transition-colors">
                  <th className="h-10 px-4 text-left align-middle font-medium text-muted-foreground">Company</th>
                  <th className="h-10 px-4 text-left align-middle font-medium text-muted-foreground">Role</th>
                  <th className="h-10 px-4 text-left align-middle font-medium text-muted-foreground">Deleted Date</th>
                  <th className="h-10 px-4 text-left align-middle font-medium text-muted-foreground">Time Remaining</th>
                  <th className="h-10 px-4 text-right align-middle font-medium text-muted-foreground">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b transition-colors hover:bg-muted/50">
                  <td className="p-4 align-middle font-medium">Stripe</td>
                  <td className="p-4 align-middle text-muted-foreground">Frontend Engineer</td>
                  <td className="p-4 align-middle text-muted-foreground">Yesterday</td>
                  <td className="p-4 align-middle text-destructive font-medium">14 days</td>
                  <td className="p-4 align-middle text-right">
                    <div className="flex justify-end gap-2">
                      <Button variant="outline" size="sm" className="gap-1">
                        <RefreshCw className="h-3 w-3" />
                        Restore
                      </Button>
                      <Button variant="destructive" size="sm" className="gap-1">
                        <Trash2 className="h-3 w-3" />
                        Purge
                      </Button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
