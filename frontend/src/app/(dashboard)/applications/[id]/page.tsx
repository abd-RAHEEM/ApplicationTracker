"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Clock, Info } from "lucide-react";
import Link from "next/link";

export default function ApplicationDetailPage({ params }: { params: { id: string } }) {
  return (
    <div className="flex flex-col gap-6 max-w-5xl">
      <div className="flex items-center gap-4">
        <Link href="/applications">
          <Button variant="outline" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Google - Software Engineer</h2>
          <p className="text-muted-foreground">Last updated 2 days ago</p>
        </div>
        <div className="ml-auto flex gap-2">
          <Button variant="outline">Update Status</Button>
          <Button variant="destructive">Delete</Button>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Timeline</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-8 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-muted before:to-transparent">
              
              <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                <div className="flex items-center justify-center w-10 h-10 rounded-full border border-white bg-blue-100 text-blue-800 shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 shadow">
                  <Clock className="w-5 h-5" />
                </div>
                <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-4 rounded border bg-card shadow-sm">
                  <div className="flex items-center justify-between space-x-2 mb-1">
                    <div className="font-bold text-slate-900">Applied</div>
                    <time className="text-xs font-medium text-blue-500">2026-06-01 10:00</time>
                  </div>
                  <div className="text-sm text-slate-500">Source: Gmail Parse (Thank you for applying)</div>
                </div>
              </div>

            </div>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Info className="h-4 w-4" />
                Parser Confidence
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Company (Google)</span>
                <span className="font-medium text-green-600">95%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Role (SWE)</span>
                <span className="font-medium text-amber-500">82%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Status (Applied)</span>
                <span className="font-medium text-green-600">97%</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
