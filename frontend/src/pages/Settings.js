import React, { useState, useEffect } from 'react';
import { Card } from 'primereact/card';
import { InputText } from 'primereact/inputtext';
import { Button } from 'primereact/button';
import { Message } from 'primereact/message';
import { ProgressSpinner } from 'primereact/progressspinner';
import { setApiKey, checkApiKey } from '../services/api';

const Settings = () => {
  const [apiKey, setApiKeyValue] = useState('');
  const [saved, setSaved] = useState(false);
  const [validating, setValidating] = useState(false);
  const [keyValid, setKeyValid] = useState(null);

  useEffect(() => {
    // Load saved API key from localStorage
    const storedApiKey = localStorage.getItem('api_key');
    if (storedApiKey) {
      setApiKeyValue(storedApiKey);
      validateApiKey(storedApiKey);
    }
  }, []);

  const validateApiKey = async (key) => {
    setValidating(true);
    try {
      // First set the key so it's used in the validation request
      setApiKey(key);
      // Then check if it's valid
      const isValid = await checkApiKey();
      setKeyValid(isValid);
    } catch (error) {
      console.error('Error validating API key:', error);
      setKeyValid(false);
    } finally {
      setValidating(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Save API key and validate it
    setApiKey(apiKey);
    await validateApiKey(apiKey);
    
    if (keyValid) {
      window.showToast('success', 'Success', 'API key saved and validated successfully!');
    } else {
      window.showToast('error', 'Error', 'API key saved but validation failed. Please check your key.');
    }
    
    setSaved(true);
    
    // Reset saved message after 3 seconds
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="grid">
      <div className="col-12">
        <h1 className="mb-4">Settings</h1>
      </div>
      
      <div className="col-12 md:col-8 lg:col-6">
        <Card title="API Configuration" subTitle="Enter your API key to connect to the Spend Analysis backend">
          {saved && (
            <Message 
              severity={keyValid ? "success" : "error"} 
              text={keyValid ? "Settings saved successfully!" : "API key saved but validation failed"} 
              className="w-full mb-3" 
            />
          )}
          
          {keyValid !== null && !validating && (
            <Message 
              severity={keyValid ? "success" : "error"} 
              text={keyValid ? "API key is valid" : "API key is invalid"} 
              className="w-full mb-3" 
            />
          )}
          
          {validating && (
            <div className="flex align-items-center mb-3">
              <ProgressSpinner style={{width: '30px', height: '30px'}} />
              <span className="ml-2">Validating API key...</span>
            </div>
          )}
          
          <form onSubmit={handleSubmit} className="p-fluid">
            <div className="field">
              <label htmlFor="apiKey" className="font-bold">API Key</label>
              <InputText
                id="apiKey"
                value={apiKey}
                onChange={(e) => setApiKeyValue(e.target.value)}
                placeholder="Enter your API key"
                required
                autoComplete="off"
              />
              <small className="text-secondary">
                This key is stored locally in your browser. The default key from creds.json is "POOP".
              </small>
            </div>
            
            <Button 
              label="Save Settings" 
              type="submit" 
              icon="pi pi-save"
              className="mt-3"
              disabled={validating}
            />
          </form>
        </Card>
      </div>
      
      <div className="col-12 md:col-8 lg:col-6 mt-3">
        <Card title="About" subTitle="Spend Analysis Application">
          <p>
            Spend Analysis helps you track and visualize your spending habits by analyzing
            your bank and credit card statements.
          </p>
          <p className="font-bold">
            Version: 1.0.0
          </p>
        </Card>
      </div>
    </div>
  );
};

export default Settings;
