import React, { useState, useCallback } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { ProgressBar } from 'primereact/progressbar';
import { Message } from 'primereact/message';
import { useDropzone } from 'react-dropzone';
import { uploadPdfFile } from '../services/api';

const FileUpload = () => {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadResults, setUploadResults] = useState([]);
  const [progress, setProgress] = useState(0);

  const onDrop = useCallback((acceptedFiles) => {
    // Filter for PDF files only
    const pdfFiles = acceptedFiles.filter(
      file => file.type === 'application/pdf'
    );

    // Add new files to current files
    setFiles(currentFiles => [...currentFiles, ...pdfFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    }
  });

  const removeFile = (file) => {
    setFiles(currentFiles => currentFiles.filter(f => f !== file));
  };

  const uploadFiles = async () => {
    if (files.length === 0) {
      window.showToast('warn', 'Warning', 'Please add some PDF files to upload');
      return;
    }

    setUploading(true);
    setProgress(0);
    setUploadResults([]);
    
    const results = [];
    const totalFiles = files.length;

    for (let i = 0; i < totalFiles; i++) {
      const file = files[i];
      const progressPercent = Math.round((i / totalFiles) * 100);
      setProgress(progressPercent);

      try {
        const result = await uploadPdfFile(file);
        results.push({
          filename: file.name,
          success: true,
          message: result.message,
        });
        window.showToast('success', 'Success', `Successfully processed ${file.name}`);
      } catch (error) {
        console.error(`Error uploading ${file.name}:`, error);
        results.push({
          filename: file.name,
          success: false,
          message: error.response?.data?.error || 'Upload failed',
        });
        window.showToast('error', 'Error', `Failed to process ${file.name}`);
      }
    }

    setProgress(100);
    setUploadResults(results);
    setUploading(false);
    setFiles([]);
  };

  const actionBodyTemplate = (rowData) => {
    return (
      <Button 
        icon="pi pi-times" 
        className="p-button-rounded p-button-danger p-button-text"
        onClick={() => removeFile(rowData)}
        disabled={uploading}
      />
    );
  };

  const formatFileSize = (size) => {
    return `${(size / 1024).toFixed(1)} KB`;
  };

  return (
    <div className="grid">
      <div className="col-12">
        <h1 className="mb-4">Upload Bank Statements</h1>
      </div>
      
      <div className="col-12">
        <div {...getRootProps({ className: 'dropzone-container' })}>
          <input {...getInputProps()} />
          <i className="pi pi-upload" style={{ fontSize: '3rem', color: 'var(--primary-color)' }}></i>
          <h3 className="mt-3">Drag & drop PDF files here</h3>
          <p className="text-secondary">
            {isDragActive
              ? "Drop the files here..."
              : "or click to select files"}
          </p>
        </div>
      </div>

      {files.length > 0 && (
        <div className="col-12 mb-4">
          <Card title="Selected Files">
            <DataTable value={files} size="small" responsiveLayout="scroll">
              <Column field="name" header="Filename" />
              <Column body={(rowData) => formatFileSize(rowData.size)} header="Size" />
              <Column body={actionBodyTemplate} style={{ width: '8rem' }} />
            </DataTable>
            
            <div className="mt-3">
              <Button 
                label={uploading ? 'Uploading...' : `Upload ${files.length} File${files.length !== 1 ? 's' : ''}`} 
                icon="pi pi-upload" 
                onClick={uploadFiles} 
                disabled={uploading}
                className="w-full"
              />
            </div>
          </Card>
        </div>
      )}

      {uploading && (
        <div className="col-12 mt-4">
          <Card title="Upload Progress">
            <ProgressBar 
              value={progress} 
              showValue={true} 
              className="mb-3" 
            />
          </Card>
        </div>
      )}

      {uploadResults.length > 0 && (
        <div className="col-12 mt-4">
          <Card title="Upload Results">
            <DataTable value={uploadResults} responsiveLayout="scroll">
              <Column field="filename" header="Filename" />
              <Column field="message" header="Message" />
              <Column 
                body={(rowData) => (
                  <span className={`p-badge p-component ${rowData.success ? 'p-badge-success' : 'p-badge-danger'}`}>
                    {rowData.success ? 'Success' : 'Failed'}
                  </span>
                )} 
                header="Status" 
              />
            </DataTable>
          </Card>
        </div>
      )}
    </div>
  );
};

export default FileUpload;
