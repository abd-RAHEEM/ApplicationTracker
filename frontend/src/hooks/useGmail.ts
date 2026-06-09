import { useState } from 'react';
import { apiClient } from "@/lib/api-client";
import { useAuthStore } from '@/store/auth-store';
import { InitialImportConfigRequest } from '@/types/gmail';
import { UserRead } from '@/types/auth';

export const useGmail = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { setUser } = useAuthStore();

  const getAuthUrl = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Note: apiClient already has baseURL set to /v1, so just use /gmail/auth-url
      const { data } = await apiClient.get<{ auth_url: string }>('/gmail/auth-url');
      // Redirect user to Google OAuth consent screen
      window.location.href = data.auth_url;
    } catch (err: any) {
      const message =
        err.response?.data?.error?.message ||
        err.response?.data?.message ||
        'Failed to get authorization URL';
      setError(message);
      setIsLoading(false); // Reset loading on error (success keeps it loading during redirect)
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
      await apiClient.post('/gmail/onboarding/complete', payload);
      
      // Refresh user state to reflect completed onboarding
      const { data: userWrapper } = await apiClient.get<{ data: UserRead }>('/users/me');
      setUser(userWrapper.data);
    } catch (err: any) {
      const message =
        err.response?.data?.error?.message ||
        err.response?.data?.message ||
        'Failed to complete onboarding configuration';
      setError(message);
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
