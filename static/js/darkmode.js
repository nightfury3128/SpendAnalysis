document.addEventListener('DOMContentLoaded', () => {
  const themeToggle = document.getElementById('theme-toggle');
  const currentTheme = localStorage.getItem('theme') || 'light';

  // Set theme based on localStorage
  if (currentTheme === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
    themeToggle.checked = true;
  }

  // Theme toggle functionality
  themeToggle.addEventListener('change', function() {
    if (this.checked) {
      document.documentElement.setAttribute('data-theme', 'dark');
      localStorage.setItem('theme', 'dark');
      updateCharts('dark');
    } else {
      document.documentElement.setAttribute('data-theme', 'light');
      localStorage.setItem('theme', 'light');
      updateCharts('light');
    }
  });
  
  // Function to update chart themes when switching
  function updateCharts(theme) {
    // If using a charting library that supports theme updates
    if (window.updateChartThemes) {
      window.updateChartThemes(theme);
    }
  }
  
  // File upload preview functionality
  const fileInput = document.getElementById('file-input');
  const fileLabel = document.querySelector('.file-name');
  const uploadArea = document.querySelector('.file-upload-area');
  
  if (fileInput && uploadArea) {
    uploadArea.addEventListener('click', () => {
      fileInput.click();
    });
    
    fileInput.addEventListener('change', (e) => {
      if (fileInput.files.length) {
        fileLabel.textContent = fileInput.files[0].name;
      }
    });
  }
});
