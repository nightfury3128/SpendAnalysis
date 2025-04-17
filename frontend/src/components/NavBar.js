import React from 'react';
import { Menubar } from 'primereact/menubar';
import { useNavigate, useLocation } from 'react-router-dom';
import { FaChartPie } from 'react-icons/fa';

const NavBar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  
  const items = [
    {
      label: 'Dashboard',
      icon: 'pi pi-chart-pie',
      command: () => navigate('/'),
      className: location.pathname === '/' ? 'p-menuitem-active' : ''
    },
    {
      label: 'Upload Files',
      icon: 'pi pi-upload',
      command: () => navigate('/upload'),
      className: location.pathname === '/upload' ? 'p-menuitem-active' : ''
    },
    {
      label: 'Settings',
      icon: 'pi pi-cog',
      command: () => navigate('/settings'),
      className: location.pathname === '/settings' ? 'p-menuitem-active' : ''
    }
  ];

  const start = (
    <div className="flex align-items-center" onClick={() => navigate('/')} style={{cursor: 'pointer'}}>
      <FaChartPie className="mr-2" style={{ fontSize: '1.5rem' }} />
      <span className="font-bold text-xl">Spend Analysis</span>
    </div>
  );

  return (
    <div className="card">
      <Menubar model={items} start={start} className="shadow-2 mb-5" />
    </div>
  );
};

export default NavBar;
