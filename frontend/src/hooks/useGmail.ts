import { useState } from 'react';
import { apiClient, apiPost } from "@/lib/api-client";
import { useAuthStore } from '@/store/auth-store';
import { OAuthUrlResponse, InitialImportConfigRequest } from '@/types/gmail';
import { UserRead } from '@/types/auth';

export const useGmail = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { setUser } = useAuthStore();

  const getAuthUrl = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<OAuthUrlResponse>('/v1/gmail/auth-url');
      // Redirect user to Google OAuth consent screen
      window.location.href = data.auth_url;
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to get authorization URL');
    } finally {
      setIsLoading(false);
    }
  };

  const completeOnboarding = async (importRange: string, importFrom: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const payload: InitialImportConfigRequest = { 
        import_range: importRange,
        import_from: importFrom 
      };
      await apiClient.post('/v1/gmail/onboarding/complete', payload);
      
      // Update local user state so they pass the onboarding gate
      const { data: user } = await apiClient.get<UserRead>('/v1/users/me');
      setUser(user);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to complete onboarding configuration');
      throw err; // Re-throw so the component can stop progression
    } finally {
      setIsLoading(false);
    }
  };

  return {
    getAuthUrl,
    completeOnboarding,
    isLoading,
    error,
  };
};
