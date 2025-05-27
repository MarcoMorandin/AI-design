import React from 'react';

const Footer = () => {
  const currentYear = new Date().getFullYear();
  
  return (
    <footer className="py-6 px-10 text-center text-sm text-slate-500 border-t border-slate-200 bg-white">
      © {currentYear} Academix. All rights reserved.
    </footer>
  );
};

export default Footer;
