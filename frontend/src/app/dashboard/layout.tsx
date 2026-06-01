import { redirect } from 'next/navigation';
import { cookies } from 'next/headers';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const hasToken = cookies().has('access_token');
  if (!hasToken) {
    redirect('/login');
  }

  return (
    <div className="min-h-screen bg-muted/20">
      <header className="bg-white border-b h-16 flex items-center px-6">
        <h1 className="text-xl font-bold text-primary">JobTracker</h1>
      </header>
      <main className="max-w-7xl mx-auto p-6">
        {children}
      </main>
    </div>
  );
}
