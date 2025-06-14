import React from 'react';
import AuthLayout from '../components/layout/AuthLayout';
import { useAuth } from '../context/AuthContext';

const LoginPage = () => {
  const { login } = useAuth();
  
  return (
    <AuthLayout>
      <div className="flex flex-1 justify-center items-center py-10 px-4 sm:px-6 lg:px-8">
        <div className="bg-white shadow-xl rounded-xl p-8 sm:p-12 w-full max-w-lg">
          <div className="text-center">
            <svg className="w-16 h-16 text-blue-600 mx-auto mb-6" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.338 0 4.5 4.5 0 0 1-1.41 8.775H6.75Z" strokeLinecap="round" strokeLinejoin="round"></path>
            </svg>
            <h2 className="text-3xl font-bold text-slate-800 tracking-tight mb-2">Welcome Back</h2>
            <p className="text-slate-600 text-base mb-8">Sign in to access your academic files.</p>
          </div>
          <button 
            onClick={login}
            className="w-full flex items-center justify-center gap-3 rounded-lg h-12 px-6 bg-blue-600 hover:bg-blue-700 text-white text-base font-semibold transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            <svg className="w-5 h-5" height="48px" viewBox="0 0 48 48" width="48px" xmlns="http://www.w3.org/2000/svg">
              <path d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z" fill="#FFC107"></path>
              <path d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z" fill="#FF3D00"></path>
              <path d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z" fill="#4CAF50"></path>
              <path d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z" fill="#1976D2"></path>
            </svg>
            <span className="truncate">Login with your google account</span>
          </button>
          <p className="text-xs text-slate-500 text-center mt-8">
            By signing in, you agree to our <a className="text-blue-600 hover:underline" href="#">Terms of Service</a> and <a className="text-blue-600 hover:underline" href="#">Privacy Policy</a>.
          </p>
        </div>
      </div>
    </AuthLayout>
  );
};

export default LoginPage;
