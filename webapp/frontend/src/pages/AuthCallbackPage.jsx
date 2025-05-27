import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const AuthCallbackPage = () => {
  const [searchParams] = useSearchParams();
  const { handleCallback } = useAuth();
  const navigate = useNavigate();
  
  useEffect(() => {
    const token = searchParams.get('token');
    
    if (token) {
      handleCallback(token);
      navigate('/dashboard', { replace: true });
    } else {
      // Redirect to login page if no token is received
      navigate('/login', { replace: true });
    }
  }, [searchParams, handleCallback, navigate]);
  
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-slate-50">
      <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-600"></div>
      <p className="mt-4 text-slate-600">Authenticating...</p>
    </div>
  );
};

export default AuthCallbackPage;
