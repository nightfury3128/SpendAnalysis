import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Toast } from 'primereact/toast';
import { useRef } from 'react';
import NavBar from './components/NavBar';
import Dashboard from './pages/Dashboard';
import FileUpload from './pages/FileUpload';
import Settings from './pages/Settings';
import './App.css';

function App() {
  const toast = useRef(null);

  // Make toast accessible globally
  window.showToast = (severity, summary, detail) => {
    if (toast.current) {
      toast.current.show({ severity, summary, detail, life: 3000 });
    }
  };

  return (
    <div className="App">
      <Toast ref={toast} position="bottom-right" />
      <NavBar />
      <div className="p-3">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/upload" element={<FileUpload />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </div>
    </div>
  );
}

export default App;
