import { redirect } from 'next/navigation';
import { cookies } from 'next/headers';

export default function OnboardingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Note: in a real app, middleware should protect this route.
  // We can do a basic check here.
  const hasToken = cookies().has('access_token');
  if (!hasToken) {
    redirect('/login');
  }

  return (
    <div className="min-h-screen bg-muted/40 flex items-center justify-center p-4">
      <div className="max-w-2xl w-full">
        {children}
      </div>
    </div>
  );
}
