import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const Header = () => {
  const { user, logout } = useAuth();
  
  return (
    <header className="flex items-center justify-between whitespace-nowrap border-b border-solid border-gray-200 bg-white px-6 sm:px-10 py-4 shadow-sm">
      <div className="flex items-center gap-6 sm:gap-8">
        <div className="flex items-center gap-3 text-blue-600">
          <div className="size-6 text-[#3d98f4]">
            <svg fill="none" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
              <path d="M24 45.8096C19.6865 45.8096 15.4698 44.5305 11.8832 42.134C8.29667 39.7376 5.50128 36.3314 3.85056 32.3462C2.19985 28.361 1.76794 23.9758 2.60947 19.7452C3.451 15.5145 5.52816 11.6284 8.57829 8.5783C11.6284 5.52817 15.5145 3.45101 19.7452 2.60948C23.9758 1.76795 28.361 2.19986 32.3462 3.85057C36.3314 5.50129 39.7376 8.29668 42.134 11.8833C44.5305 15.4698 45.8096 19.6865 45.8096 24L24 24L24 45.8096Z" fill="currentColor"></path>
            </svg>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-[#3d98f4]">Academix</h1>
        </div>
        
        {user && (
          <nav className="hidden sm:flex items-center gap-6">
            <Link className="text-sm font-medium text-gray-700 hover:text-[#3d98f4]" to="/dashboard">Dashboard</Link>
            <Link className="text-sm font-medium text-gray-700 hover:text-[#3d98f4]" to="/documents">Documents</Link>
            <Link className="text-sm font-medium text-gray-700 hover:text-[#3d98f4]" to="/tasks">Tasks</Link>
            <Link className="text-sm font-medium text-gray-700 hover:text-[#3d98f4]" to="/calendar">Calendar</Link>
          </nav>
        )}
      </div>
      
      {user ? (
        <div className="flex items-center gap-4">
          <label className="relative hidden md:flex flex-col min-w-40 !h-10 max-w-xs">
            <div className="flex w-full flex-1 items-stretch rounded-lg h-full">
              <div className="text-gray-400 flex border-none bg-gray-100 items-center justify-center pl-3 rounded-l-lg border-r-0">
                <svg fill="currentColor" height="20px" viewBox="0 0 256 256" width="20px" xmlns="http://www.w3.org/2000/svg">
                  <path d="M229.66,218.34l-50.07-50.06a88.11,88.11,0,1,0-11.31,11.31l50.06,50.07a8,8,0,0,0,11.32-11.32ZM40,112a72,72,0,1,1,72,72A72.08,72.08,0,0,1,40,112Z"></path>
                </svg>
              </div>
              <input className="form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-r-lg text-gray-900 focus:outline-0 focus:ring-2 focus:ring-[#3d98f4] border-none bg-gray-100 focus:border-none h-full placeholder:text-gray-500 px-3 text-sm font-normal leading-normal" placeholder="Search courses..." />
            </div>
          </label>
          
          <button aria-label="Notifications" className="flex items-center justify-center rounded-lg h-10 w-10 bg-gray-100 hover:bg-gray-200 text-gray-700">
            <svg fill="currentColor" height="20px" viewBox="0 0 256 256" width="20px" xmlns="http://www.w3.org/2000/svg">
              <path d="M221.8,175.94C216.25,166.38,208,139.33,208,104a80,80,0,1,0-160,0c0,35.34-8.26,62.38-13.81,71.94A16,16,0,0,0,48,200H88.81a40,40,0,0,0,78.38,0H208a16,16,0,0,0,13.8-24.06ZM128,216a24,24,0,0,1-22.62-16h45.24A24,24,0,0,1,128,216ZM48,184c7.7-13.24,16-43.92,16-80a64,64,0,1,1,128,0c0,36.05,8.28,66.73,16,80Z"></path>
            </svg>
          </button>
          
          <div className="bg-center bg-no-repeat aspect-square bg-cover rounded-full size-10 border-2 border-gray-300 hover:border-[#3d98f4]" 
               style={{ backgroundImage: user.profile_image ? `url(${user.profile_image})` : "none" }}
               onClick={logout}>
          </div>
        </div>
      ) : null}
    </header>
  );
};

export default Header;
