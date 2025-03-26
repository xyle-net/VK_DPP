'use client';

import dynamic from 'next/dynamic';

// Use dynamic import with SSR disabled for the entire component
const HomeComponent = dynamic(() => import('./components/HomeComponent'), {
  ssr: false,
  loading: () => (
    <div className="min-h-screen bg-[#808AFC] flex items-center justify-center p-8">
      <div className="bg-white rounded-2xl p-10 max-w-4xl w-full text-center">
        Загрузка...
      </div>
    </div>
  ),
});

export default function Home() {
  return <HomeComponent />;
}
