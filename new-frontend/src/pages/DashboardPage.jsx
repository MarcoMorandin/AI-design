import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import MainLayout from '../components/layout/MainLayout';
import { userService } from '../services/api';

const DashboardPage = () => {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchCourses = async () => {
      try {
        const data = await userService.getCourses();
        setCourses(data.courses || []);
      } catch (err) {
        setError('Failed to load courses. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchCourses();
  }, []);

  // Sample images for course cards
  const sampleImages = [
    'https://lh3.googleusercontent.com/aida-public/AB6AXuAnggYSCJ4YiEaqUwpZusrkqmNcSLmdMXYmoifrk28Cz-2xkgSIckkhO2jaAKT3o2fCiSfj-g0263lkkZErFEAapBzRkQba0QWkLw9k-_ZAPFOh32pSsCtMcnj8T7A06Ewd4ludF6NInnQC_wNttspuqH9u7LNcqrLmWOFlaMROxWWwkM7GFDRoSIBvvvRh5HFin_1abh39Zgmv-OdclHMtiCtmpZY1tmvcUL9YjF8DMZik13YcBbU1c1bGoNi9iZ1Br0vw5TmUDIK2',
    'https://lh3.googleusercontent.com/aida-public/AB6AXuCeoZ_jZJI4w4bY7jG8LKasToDWF5TML3dwnJplvVDkaND-CV77r9vdLb_SiTSEDp9rD53JR2QWL8aCS1bFuuVqgVF4L_rot6zZQdHw23Ydz08-8CvhYZuXO0iHuzRk_sKsBpw2Lq2ED6SYzCtN8lZWJRFcJ0Fd20LcDYtO959-bMNfwZYwG4TerThoYpzYtb3rOOy-Jf2t1o6FnKTLW84wcCO4Z5aZ_3_r8jGHwbyEbQ_MU1lTGjL1JIeYSi4qoCMpeHkZF-39iCeZ',
    'https://lh3.googleusercontent.com/aida-public/AB6AXuCLOXBiNRRzFrxbjDT3euWELFGTjhhE6aJfHJvWnkQ9T0w-vRiLj9cyDb5JGrhs9yzq-gX9hwSw4_1dsKBhN4HfUVlMzZe0WdiJ5boKPFSvPFsFpO-M21mPO08QydHYgIOGWJI3D4Tz2tS75CYfGxxZvMZJslMq-1p4wpJ9thAFmIKENKVrZCu1_EdcmRqsnFoIfkUDzfMebvg8ou3GQHyY7tjbrqeqH6JiiJaNLdqb9EHPMng2kHQk_bYFNIwYTQ-zHjL3RL0B2iU1',
    'https://lh3.googleusercontent.com/aida-public/AB6AXuBbkhTi54EwOcPtolNVDuOcEvJrCocE4-rROiCXdP2LZiSWew0bPrLTx_TPK7dgWE64D1CvWbueDSWDiYz7jurvsKJUxLlIK2nGTpzsK1xA450AtHtQ-L5aGDXIlpK-iWusY1sfcv3zz7TC6xU2agfw-AzzN-oXGaSmxgtkHYD0eUNVsQRTM2HDvHOV4dMI-ClzbcTkU6svhhjnX9et1W82J4BzLXk5bH7ijG30piANypGERPOBHa7usnc9gU6OHqlVOYa4ygxOIPK6',
    'https://lh3.googleusercontent.com/aida-public/AB6AXuBp3uRMYhyTSf_6wMPMQDBRIdp-msoXxYAnRWWh0o9nD3Yt4PSTNJjme7PW4xkzHhDxH_GijrmrdAXNYazqzVtzfF4CkpceDzqGQrJPEKekVC2yIYJeTB0AwkhocCIFEgT71fskU8b-5ah_DrbrxwMv87MmKqwdgB6Oxj-3dWz5q2lcRkXu-U7fO7MdwxgTiOg2RCT03kGUoyFAesvQLMKDDf0LgdebpXmFgj9yPLnQZ8J42GWBuXliYYEDB7HmcQEih887taHbinFz',
  ];

  // Default course descriptions if backend doesn't provide them
  const defaultDescriptions = [
    'Learn the fundamentals of computer science, including algorithms, data structures, and programming concepts.',
    'Explore the concepts of limits, derivatives, and integrals in single-variable calculus.',
    'Study vector spaces, linear transformations, and matrices.',
    'Understand probability theory, statistical inference, and data analysis.',
    'Dive into advanced data structures and algorithm design techniques.'
  ];

  return (
    <MainLayout>
      <main className="flex-1 py-8 px-4 sm:px-6 md:px-10 lg:px-16 xl:px-24">
        <div className="max-w-6xl mx-auto">
          {loading ? (
            <div className="flex justify-center items-center h-64">
              <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-600"></div>
            </div>
          ) : error ? (
            <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg p-4">
              {error}
            </div>
          ) : (
            <>
              <div className="mb-8">
                <h2 className="text-gray-900 text-3xl font-bold leading-tight">My Courses</h2>
              </div>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {courses && courses.length > 0 ? (
                  courses.map((course, index) => (
                    <Link 
                      key={course.id}
                      to={`/courses/${course.id}`}
                      className="course-card block bg-white rounded-xl shadow-lg overflow-hidden hover:shadow-xl transition-transform hover:-translate-y-1"
                    >
                      <div 
                        className="w-full h-48 bg-center bg-no-repeat bg-cover" 
                        style={{
                          backgroundImage: `url("${sampleImages[index % sampleImages.length]}")`
                        }}
                      ></div>
                      <div className="p-6">
                        <h3 className="text-gray-900 text-lg font-semibold leading-tight mb-2">{course.name}</h3>
                        <p className="text-gray-600 text-sm font-normal leading-normal">
                          {defaultDescriptions[index % defaultDescriptions.length]}
                        </p>
                      </div>
                    </Link>
                  ))
                ) : (
                  <div className="col-span-full bg-white rounded-xl shadow p-6 text-center">
                    <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <h3 className="text-lg font-semibold mb-2">No courses found</h3>
                    <p className="text-gray-600">You don't have any courses yet.</p>
                  </div>
                )}
                
                {/* Add new course card */}
                <Link 
                  to="/courses/new" 
                  className="course-card block bg-white rounded-xl shadow-lg overflow-hidden hover:shadow-xl transition-transform hover:-translate-y-1"
                >
                  <div className="w-full h-48 bg-center bg-no-repeat bg-cover flex items-center justify-center bg-gray-100">
                    <svg className="w-16 h-16 text-gray-400" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path d="M12 4.5v15m7.5-7.5h-15" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </div>
                  <div className="p-6">
                    <h3 className="text-gray-900 text-lg font-semibold leading-tight mb-2">Add New Course</h3>
                    <p className="text-gray-600 text-sm font-normal leading-normal">
                      Create a new course to organize your materials.
                    </p>
                  </div>
                </Link>
              </div>
            </>
          )}
        </div>
      </main>
    </MainLayout>
  );
};

export default DashboardPage;
