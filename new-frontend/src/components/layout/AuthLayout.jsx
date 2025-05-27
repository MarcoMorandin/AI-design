import React from 'react';
import Footer from './Footer';

const AuthLayout = ({ children }) => {
  return (
    <div className="relative flex size-full min-h-screen flex-col group/design-root overflow-x-hidden bg-slate-50">
      <div className="layout-container flex h-full grow flex-col">
        <header className="flex items-center justify-between whitespace-nowrap border-b border-solid border-b-slate-200 px-10 py-5 bg-white">
          <div className="flex items-center gap-3 text-slate-900">
            <svg className="w-8 h-8 text-blue-600" fill="none" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
              <path d="M24 4C25.7818 14.2173 33.7827 22.2182 44 24C33.7827 25.7818 25.7818 33.7827 24 44C22.2182 33.7827 14.2173 25.7818 4 24C14.2173 22.2182 22.2182 14.2173 24 4Z" fill="currentColor"></path>
            </svg>
            <h2 className="text-slate-900 text-xl font-bold tracking-tight">Academix</h2>
          </div>
        </header>
        
        <main className="flex-1">
          {children}
        </main>
        
        <Footer />
      </div>
    </div>
  );
};

export default AuthLayout;
