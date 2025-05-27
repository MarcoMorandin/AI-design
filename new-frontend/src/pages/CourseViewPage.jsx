import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import MainLayout from '../components/layout/MainLayout';
import MarkdownMessage from '../components/MarkdownMessage';
import { userService, orchestratorService } from '../services/api';

const CourseViewPage = () => {
  const { courseId } = useParams();
  const [course, setCourse] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Welcome to your course! How can I help you today?' }
  ]);
  const [isSending, setIsSending] = useState(false);
  
  useEffect(() => {
    const fetchCourseData = async () => {
      try {
        const data = await userService.getCourseById(courseId);
        console.log('Fetched course data:', data);
        setCourse(data);
      } catch (error) {
        setError('Failed to load course. Please try again later.');
        console.error(error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchCourseData();
  }, [courseId]);
  
  const sendMessage = async () => {
    if (!message.trim()) return;
    
    try {
      setIsSending(true);
      
      // Capture selected files info for the message
      const selectedFileIds = Array.from(selectedFiles);
      const selectedFileNames = getSelectedFileNames();
      
      // Create enhanced message with Google Drive IDs appended
      let enhancedMessage = message;
      if (selectedFileIds.length > 0) {
        enhancedMessage += `\n\nFile IDs: ${selectedFileIds.join(', ')}`;
      }
      
      // Add user message to the chat with file context (show original message to user)
      const userMessage = { 
        role: 'user', 
        content: message, // Show original message without IDs in UI
        files: selectedFileIds.length > 0 ? selectedFileNames : null
      };
      setMessages(prev => [...prev, userMessage]);
      
      // Clear input but keep selected files visible until response
      setMessage('');
      
      // Send enhanced message to orchestrator with selected file IDs
      const response = await orchestratorService.sendMessage(enhancedMessage, null, { 
        id: courseId,
        selected_files: selectedFileIds
      });
      
      // Create a session to track the conversation
      const taskId = response.task_id;
      
      if (!taskId) {
        console.error('No task_id returned from orchestrator:', response);
        setMessages(prev => 
          prev.filter(msg => !msg.temporary)
            .concat({ 
              role: 'assistant', 
              content: 'Sorry, there was an error connecting to the assistant service.' 
            })
        );
        setIsSending(false);
        // Clear selected files when no task_id
        setSelectedFiles(new Set());
        return;
      }
      
      // Add a temporary thinking message
      setMessages(prev => [...prev, { role: 'assistant', content: 'Thinking...', temporary: true }]);
      
      // Poll for response
      const polling = setInterval(async () => {
        try {
          const taskResponse = await orchestratorService.getTaskStatus(taskId);
          
          if (taskResponse.status === 'completed') {
            clearInterval(polling);
            
            // Replace the temporary message with the real response
            setMessages(prev => 
              prev.filter(msg => !msg.temporary)
                .concat({ role: 'assistant', content: taskResponse.content })
            );
            setIsSending(false);
            // Clear selected files after successful response
            setSelectedFiles(new Set());
          } else if (taskResponse.status === 'failed' || taskResponse.status === 'canceled') {
            clearInterval(polling);
            
            // Replace temporary message with error
            setMessages(prev => 
              prev.filter(msg => !msg.temporary)
                .concat({ 
                  role: 'assistant', 
                  content: 'Sorry, I encountered an error processing your request.' 
                })
            );
            setIsSending(false);
            // Clear selected files even on error
            setSelectedFiles(new Set());
          }
        } catch (error) {
          console.error('Error polling task status:', error);
          clearInterval(polling);
          setIsSending(false);
          // Clear selected files on polling error
          setSelectedFiles(new Set());
        }
      }, 1000);
    } catch (error) {
      console.error('Error sending message:', error);
      setIsSending(false);
      
      // Show error to the user
      setMessages(prev => 
        [...prev, { 
          role: 'assistant', 
          content: `Error: ${error.message || 'Failed to send message to assistant.'}` 
        }]
      );
      // Clear selected files on send error
      setSelectedFiles(new Set());
    }
  };
  
  // State for selected files
  const [selectedFiles, setSelectedFiles] = useState(new Set());
  
  // Toggle file selection
  const toggleFileSelection = (fileId) => {
    const newSelected = new Set(selectedFiles);
    if (newSelected.has(fileId)) {
      newSelected.delete(fileId);
    } else {
      newSelected.add(fileId);
    }
    setSelectedFiles(newSelected);
  };

  // Get selected file names for display
  const getSelectedFileNames = () => {
    const selectedFileNames = [];
    
    const findFileNames = (items) => {
      if (!items) return;
      
      items.forEach(item => {
        if (!item.is_folder && selectedFiles.has(item.id)) {
          selectedFileNames.push(item.name);
        } else if (item.is_folder && item.children) {
          findFileNames(item.children);
        }
      });
    };
    
    if (course && course.items) {
      findFileNames(course.items);
    }
    
    return selectedFileNames;
  };
  
  // Render hierarchical folder structure
  const renderFolderStructure = (items, level = 0) => {
    if (!items || !items.length) return null;
    
    return items.map((item) => {
      if (item.is_folder && item.children && item.children.length > 0) {
        // This is a section folder (second level)
        return (
          <div key={item.id} className="mb-6">
            <h2 className="text-slate-800 text-xl font-semibold leading-tight tracking-tight px-1 pb-2 pt-3 border-b border-slate-200 mb-3">
              {item.name}
            </h2>
            <div className="space-y-2">
              {renderFolderStructure(item.children, level + 1)}
            </div>
          </div>
        );
      } else if (!item.is_folder) {
        // This is a file (material)
        return (
          <label key={item.id} className="flex items-center gap-x-3 p-3 hover:bg-slate-50 rounded-lg cursor-pointer transition-colors">
            <input 
              className="h-5 w-5 rounded border-slate-300 bg-white text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0 focus:border-blue-500 focus:outline-none transition-all duration-150"
              type="checkbox"
              checked={selectedFiles.has(item.id)}
              onChange={() => toggleFileSelection(item.id)}
            />
            <span className="text-slate-700 text-base font-medium leading-normal">{item.name}</span>
          </label>
        );
      } else {
        // Empty folder or other cases
        return (
          <div key={item.id} className="p-3 text-slate-500 italic">
            {item.name} (empty)
          </div>
        );
      }
    });
  };
  
  return (
    <MainLayout>
      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-600"></div>
        </div>
      ) : error ? (
        <div className="p-6">
          <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg p-4">
            {error}
          </div>
        </div>
      ) : course ? (
        <main className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 p-6">
          <div className="lg:col-span-2 bg-white rounded-xl shadow-lg p-6 flex flex-col gap-6">
            <div className="flex flex-col gap-1">
              <h1 className="text-slate-900 text-3xl font-bold leading-tight">{course.course_name}</h1>
              <p className="text-slate-500 text-sm font-normal leading-normal">Course ID: {course.course_id}</p>
            </div>
            
            <div className="space-y-4">
              {course.items && course.items.length > 0 ? (
                renderFolderStructure(course.items)
              ) : (
                <div className="p-6 text-center text-slate-500">
                  <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <h3 className="text-lg font-semibold mb-2">No materials found</h3>
                  <p className="text-gray-600">This course doesn't have any materials yet.</p>
                </div>
              )}
            </div>
          </div>
          
          <div className="bg-white rounded-xl shadow-lg flex flex-col h-[calc(100vh-110px)]">
            <div className="p-4 border-b border-slate-200">
              <h2 className="text-slate-800 text-lg font-semibold">Course Assistant</h2>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4">
              <div className="flex flex-col gap-4">
                {messages.map((msg, index) => (
                  <div 
                    key={index} 
                    className={`rounded-lg p-3 max-w-[80%] ${
                      msg.role === 'assistant' 
                        ? 'bg-blue-50 text-slate-700' 
                        : 'bg-blue-600 text-white ml-auto'
                    } ${msg.temporary ? 'opacity-70' : ''}`}
                  >
                    {msg.role === 'assistant' ? (
                      <MarkdownMessage 
                        content={msg.content} 
                        className="text-sm"
                      />
                    ) : (
                      <p className="text-sm">{msg.content}</p>
                    )}
                    {/* Show file context for user messages */}
                    {msg.role === 'user' && msg.files && msg.files.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-blue-500/30">
                        <div className="flex items-center gap-1 mb-1">
                          <svg className="w-3 h-3 text-blue-200" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                          <span className="text-xs text-blue-200">
                            {msg.files.length} file{msg.files.length > 1 ? 's' : ''} included
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {msg.files.map((fileName, fileIndex) => (
                            <span key={fileIndex} className="inline-block px-1.5 py-0.5 bg-blue-500/30 text-blue-100 text-xs rounded">
                              {fileName}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
            
            <div className="p-4 border-t border-slate-200">
              {/* Selected files display */}
              {selectedFiles.size > 0 && (
                <div className="mb-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                  <div className="flex items-center gap-2 mb-2">
                    <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <span className="text-sm font-medium text-blue-700">
                      {selectedFiles.size} file{selectedFiles.size > 1 ? 's' : ''} selected
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {getSelectedFileNames().map((fileName, index) => (
                      <span key={index} className="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                        {fileName}
                      </span>
                    ))}
                  </div>
                  <button 
                    onClick={() => setSelectedFiles(new Set())}
                    className="mt-2 text-xs text-blue-600 hover:text-blue-800 underline"
                  >
                    Clear selection
                  </button>
                </div>
              )}
              
              <div className="relative">
                <input 
                  type="text" 
                  className="w-full rounded-full border border-slate-300 py-2 pl-4 pr-10 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder={selectedFiles.size > 0 ? `Ask about the selected file${selectedFiles.size > 1 ? 's' : ''}...` : "Ask a question about this course..."}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && !isSending && sendMessage()}
                  disabled={isSending}
                />
                <button 
                  className={`absolute right-2 top-1/2 -translate-y-1/2 ${
                    isSending ? 'text-slate-400' : 'text-blue-600 hover:text-blue-800'
                  }`}
                  onClick={sendMessage}
                  disabled={isSending || !message.trim()}
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </main>
      ) : (
        <div className="p-6">
          <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 rounded-lg p-4">
            No course found with ID: {courseId}
          </div>
        </div>
      )}
    </MainLayout>
  );
};

export default CourseViewPage;
