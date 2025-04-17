# Spend Analysis Frontend

This is the React frontend for the Spend Analysis application. It allows you to upload bank statements and visualize your spending habits.

## Getting Started

### Prerequisites

- Node.js (v14 or higher)
- NPM (v6 or higher)
- The Spend Analysis backend running on http://localhost:5000

### Installation

1. Install dependencies:
   ```
   npm install
   ```

2. Start the development server:
   ```
   npm start
   ```
   
3. Open your browser and navigate to:
   ```
   http://localhost:3000
   ```

### Building for Production

```
npm run build
```

This will create an optimized production build in the `build` folder.

## Features

- Upload and process bank statement PDFs
- View spending analysis dashboard
- Track income and expenses over time
- View spending forecasts
- Analyze spending by category
- Filter and search transaction data

## Configuration

The application uses a proxy to connect to the backend API. This is configured in `package.json`:

```json
"proxy": "http://localhost:5000"
```

If your backend is running on a different URL, you can:

1. Set an environment variable in your `.env` file:
   ```
   REACT_APP_API_URL=http://your-backend-url
   ```

2. Or update the proxy in `package.json`

## API Key

You need to configure your API key in the Settings page to authenticate with the backend.

## Technologies Used

- React
- React Router
- Axios
- React Bootstrap
- Plotly.js
- React Dropzone
- React Toastify
