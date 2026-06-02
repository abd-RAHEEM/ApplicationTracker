"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useAuth } from "@/hooks/useAuth";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { Briefcase } from "lucide-react";

const loginSchema = z.object({
  username: z.string().min(1, "Username is required"),
  password: z.string().min(1, "Password is required"),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const { login, isLoggingIn } = useAuth();
  
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      username: "",
      password: "",
    },
  });

  const onSubmit = (data: LoginFormValues) => {
    login(data);
  };

  return (
    <Card className="w-full max-w-md shadow-lg border-gray-100 dark:border-gray-800 transition-all duration-300 hover:shadow-xl">
      <CardHeader className="space-y-3 text-center pb-6">
        <div className="flex justify-center mb-2">
          <div className="bg-primary/10 p-3 rounded-2xl">
            <Briefcase className="w-8 h-8 text-primary" />
          </div>
        </div>
        <CardTitle className="text-2xl font-bold tracking-tight">Welcome back</CardTitle>
        <CardDescription className="text-gray-500 dark:text-gray-400">
          Enter your credentials to access your applications
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="username" className="text-sm font-medium">Username</Label>
            <Input
              id="username"
              placeholder="johndoe"
              autoComplete="username"
              disabled={isLoggingIn}
              className={`transition-colors ${errors.username ? "border-red-500 focus-visible:ring-red-500" : ""}`}
              {...register("username")}
            />
            {errors.username && (
              <p className="text-sm text-red-500 mt-1">{errors.username.message}</p>
            )}
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="password" className="text-sm font-medium">Password</Label>
              <Link 
                href="/forgot-password" 
                className="text-xs text-primary hover:underline font-medium"
              >
                Forgot password?
              </Link>
            </div>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              disabled={isLoggingIn}
              className={`transition-colors ${errors.password ? "border-red-500 focus-visible:ring-red-500" : ""}`}
              {...register("password")}
            />
            {errors.password && (
              <p className="text-sm text-red-500 mt-1">{errors.password.message}</p>
            )}
          </div>
          <Button type="submit" className="w-full h-11 text-md" disabled={isLoggingIn}>
            {isLoggingIn ? (
              <>
                <Spinner className="mr-2 h-4 w-4" />
                Signing in...
              </>
            ) : (
              "Sign In"
            )}
          </Button>
        </form>
      </CardContent>
      <CardFooter className="flex justify-center border-t border-gray-100 dark:border-gray-800 pt-6">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Don't have an account?{" "}
          <Link href="/register" className="text-primary font-semibold hover:underline">
            Sign up
          </Link>
        </p>
      </CardFooter>
    </Card>
  );
}
