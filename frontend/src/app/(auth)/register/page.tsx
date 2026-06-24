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
import { Briefcase, Check, X } from "lucide-react";

const registerSchema = z.object({
  full_name: z.string().min(2, "Full name must be at least 2 characters"),
  username: z.string()
    .min(3, "Username must be at least 3 characters")
    .max(30, "Username must be max 30 characters")
    .regex(/^[a-zA-Z0-9_]+$/, "Username can only contain letters, numbers, and underscores"),
  password: z.string()
    .min(8, "Password must be at least 8 characters")
    .regex(/[a-z]/, "Password must contain at least one lowercase letter")
    .regex(/[A-Z]/, "Password must contain at least one uppercase letter")
    .regex(/\d/, "Password must contain at least one number")
    .regex(/[@$!%*?&_\-#^()+={}\[\]|\\:;\"'<>,.?/~`]/, "Password must contain at least one special character"),
  confirm_password: z.string(),
}).refine((data) => data.password === data.confirm_password, {
  message: "Passwords do not match",
  path: ["confirm_password"],
});

type RegisterFormValues = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const { register: registerAction, isRegistering } = useAuth();
  
  const {
    register,
    handleSubmit,
    setError,
    watch,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      full_name: "",
      username: "",
      password: "",
      confirm_password: "",
    },
  });

  const onSubmit = (data: RegisterFormValues) => {
    registerAction(
      {
        full_name: data.full_name,
        username: data.username,
        password: data.password,
        confirm_password: data.confirm_password,
      },
      {
        onError: (err: any) => {
          const fields = err.response?.data?.error?.details?.fields;
          if (fields) {
            Object.entries(fields).forEach(([field, messages]) => {
              const msg = Array.isArray(messages) ? messages[0] : String(messages);
              setError(field as keyof RegisterFormValues, {
                type: "server",
                message: msg,
              });
            });
          }
        },
      }
    );
  };

  const passwordValue = watch("password") || "";
  const passwordRules = {
    length: passwordValue.length >= 8,
    lowercase: /[a-z]/.test(passwordValue),
    uppercase: /[A-Z]/.test(passwordValue),
    number: /\d/.test(passwordValue),
    special: /[@$!%*?&_\-#^()+={}\[\]|\\:;\"'<>,.?/~`]/.test(passwordValue),
  };

  return (
    <Card className="w-full max-w-md shadow-lg border-gray-100 dark:border-gray-800 transition-all duration-300 hover:shadow-xl">
      <CardHeader className="space-y-3 text-center pb-6">
        <div className="flex justify-center mb-2">
          <div className="bg-primary/10 p-3 rounded-2xl">
            <Briefcase className="w-8 h-8 text-primary" />
          </div>
        </div>
        <CardTitle className="text-2xl font-bold tracking-tight">Create an account</CardTitle>
        <CardDescription className="text-gray-500 dark:text-gray-400">
          Sign up to track your job applications seamlessly
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="full_name" className="text-sm font-medium">Full Name</Label>
            <Input
              id="full_name"
              placeholder="John Doe"
              disabled={isRegistering}
              className={`transition-colors ${errors.full_name ? "border-red-500 focus-visible:ring-red-500" : ""}`}
              {...register("full_name")}
            />
            {errors.full_name && (
              <p className="text-sm text-red-500 mt-1">{errors.full_name.message}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="username" className="text-sm font-medium">Username</Label>
            <Input
              id="username"
              placeholder="johndoe"
              autoComplete="username"
              disabled={isRegistering}
              className={`transition-colors ${errors.username ? "border-red-500 focus-visible:ring-red-500" : ""}`}
              {...register("username")}
            />
            {errors.username ? (
              <p className="text-sm text-red-500 mt-1">{errors.username.message}</p>
            ) : (
              <p className="text-xs text-gray-500 mt-1">Username cannot be changed later.</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="password" className="text-sm font-medium">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              disabled={isRegistering}
              className={`transition-colors ${errors.password ? "border-red-500 focus-visible:ring-red-500" : ""}`}
              {...register("password")}
            />
            {passwordValue && (
              <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-100 dark:border-gray-800 space-y-1.5 mt-2">
                <p className="text-xs font-semibold text-gray-500 dark:text-gray-400">Password requirements:</p>
                <ul className="text-xs space-y-1">
                  <li className={`flex items-center space-x-1.5 ${passwordRules.length ? 'text-green-600 dark:text-green-400' : 'text-gray-400 dark:text-gray-500'}`}>
                    {passwordRules.length ? <Check className="w-3.5 h-3.5" /> : <X className="w-3.5 h-3.5" />}
                    <span>At least 8 characters</span>
                  </li>
                  <li className={`flex items-center space-x-1.5 ${passwordRules.lowercase ? 'text-green-600 dark:text-green-400' : 'text-gray-400 dark:text-gray-500'}`}>
                    {passwordRules.lowercase ? <Check className="w-3.5 h-3.5" /> : <X className="w-3.5 h-3.5" />}
                    <span>Contains lowercase letter</span>
                  </li>
                  <li className={`flex items-center space-x-1.5 ${passwordRules.uppercase ? 'text-green-600 dark:text-green-400' : 'text-gray-400 dark:text-gray-500'}`}>
                    {passwordRules.uppercase ? <Check className="w-3.5 h-3.5" /> : <X className="w-3.5 h-3.5" />}
                    <span>Contains uppercase letter</span>
                  </li>
                  <li className={`flex items-center space-x-1.5 ${passwordRules.number ? 'text-green-600 dark:text-green-400' : 'text-gray-400 dark:text-gray-500'}`}>
                    {passwordRules.number ? <Check className="w-3.5 h-3.5" /> : <X className="w-3.5 h-3.5" />}
                    <span>Contains a number</span>
                  </li>
                  <li className={`flex items-center space-x-1.5 ${passwordRules.special ? 'text-green-600 dark:text-green-400' : 'text-gray-400 dark:text-gray-500'}`}>
                    {passwordRules.special ? <Check className="w-3.5 h-3.5" /> : <X className="w-3.5 h-3.5" />}
                    <span>Contains a special character</span>
                  </li>
                </ul>
              </div>
            )}
            {errors.password && (
              <p className="text-sm text-red-500 mt-1">{errors.password.message}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirm_password" className="text-sm font-medium">Confirm Password</Label>
            <Input
              id="confirm_password"
              type="password"
              autoComplete="new-password"
              disabled={isRegistering}
              className={`transition-colors ${errors.confirm_password ? "border-red-500 focus-visible:ring-red-500" : ""}`}
              {...register("confirm_password")}
            />
            {errors.confirm_password && (
              <p className="text-sm text-red-500 mt-1">{errors.confirm_password.message}</p>
            )}
          </div>
          <Button type="submit" className="w-full h-11 text-md" disabled={isRegistering}>
            {isRegistering ? (
              <>
                <Spinner className="mr-2 h-4 w-4" />
                Creating account...
              </>
            ) : (
              "Sign Up"
            )}
          </Button>
        </form>
      </CardContent>
      <CardFooter className="flex justify-center border-t border-gray-100 dark:border-gray-800 pt-6">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Already have an account?{" "}
          <Link href="/login" className="text-primary font-semibold hover:underline">
            Sign in
          </Link>
        </p>
      </CardFooter>
    </Card>
  );
}
