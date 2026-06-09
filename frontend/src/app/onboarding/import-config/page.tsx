"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Calendar, History, ArrowRight } from "lucide-react";
import { useAuthStore } from "@/store/auth-store";
import { useGmail } from "@/hooks/useGmail";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";


type RangeOption = "1_month" | "6_months" | "1_year" | "all";

export default function ImportConfigPage() {
  const router = useRouter();
  const { user } = useAuthStore();
  const { completeOnboarding, isLoading, error } = useGmail();
  const [selectedRange, setSelectedRange] = useState<RangeOption>("6_months");

  useEffect(() => {
    // Auth guards
    if (!user) return;
    if (!user.gmail_connected) {
      router.push("/onboarding/connect-gmail");
    } else if (user.is_onboarding_completed) {
      router.push("/dashboard");
    }
  }, [user, router]);

  const handleComplete = async () => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    let importFromDate: Date;

    switch (selectedRange) {
      case "1_month":
        importFromDate = new Date(today);
        importFromDate.setMonth(importFromDate.getMonth() - 1);
        break;
      case "6_months":
        importFromDate = new Date(today);
        importFromDate.setMonth(importFromDate.getMonth() - 6);
        break;
      case "1_year":
        importFromDate = new Date(today);
        importFromDate.setFullYear(importFromDate.getFullYear() - 1);
        break;
      case "all":
        importFromDate = new Date("2004-04-01"); // Approx Gmail launch date
        break;
      default:
        importFromDate = new Date(today);
        importFromDate.setMonth(importFromDate.getMonth() - 6);
    }

    try {
      await completeOnboarding(selectedRange, importFromDate.toISOString());
      router.push("/dashboard");
    } catch (err) {
      // Error is handled in the hook
    }
  };


  const OptionCard = ({ id, title, desc, icon: Icon }: { id: RangeOption, title: string, desc: string, icon: any }) => (
    <div 
      onClick={() => setSelectedRange(id)}
      className={cn(
        "cursor-pointer border-2 rounded-xl p-4 flex items-start gap-4 transition-all duration-200",
        selectedRange === id 
          ? "border-primary bg-primary/5 shadow-md" 
          : "border-border hover:border-primary/50 hover:bg-muted/50"
      )}
    >
      <div className={cn(
        "p-2 rounded-full",
        selectedRange === id ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
      )}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <h4 className="font-semibold">{title}</h4>
        <p className="text-sm text-muted-foreground">{desc}</p>
      </div>
    </div>
  );

  return (
    <Card className="shadow-lg border-0 bg-white/50 backdrop-blur-sm">
      <CardHeader className="text-center pb-2">
        <div className="mx-auto w-12 h-12 bg-primary/10 text-primary rounded-full flex items-center justify-center mb-4">
          <History className="w-6 h-6" />
        </div>
        <CardTitle className="text-3xl font-bold">Historical Import</CardTitle>
        <CardDescription className="text-base mt-2">
          How far back should we look for job applications? We will scan your inbox
          to build your initial dashboard.
        </CardDescription>
      </CardHeader>
      
      <CardContent className="mt-6 space-y-4">
        <div className="grid gap-3">
          <OptionCard 
            id="1_month" 
            title="Last Month" 
            desc="Fastest. Good if you just started applying." 
            icon={Calendar} 
          />
          <OptionCard 
            id="6_months" 
            title="Last 6 Months" 
            desc="Recommended. Captures active and recent cycles." 
            icon={Calendar} 
          />
          <OptionCard 
            id="1_year" 
            title="Last Year" 
            desc="Comprehensive review of your recent history." 
            icon={Calendar} 
          />
          <OptionCard 
            id="all" 
            title="Everything" 
            desc="Slowest. Scans all history for maximum data." 
            icon={History} 
          />
        </div>
        
        {error && (
          <div className="p-3 bg-destructive/10 text-destructive text-sm rounded-md font-medium text-center">
            {error}
          </div>
        )}
      </CardContent>
      
      <CardFooter className="pt-6">
        <Button 
          size="lg" 
          className="w-full text-base font-semibold h-12 group"
          onClick={handleComplete}
          disabled={isLoading}
        >
          {isLoading ? (
            <><Spinner className="mr-2" size="sm" /> Saving...</>
          ) : (
            <>Complete Setup <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" /></>
          )}
        </Button>
      </CardFooter>
    </Card>
  );
}
