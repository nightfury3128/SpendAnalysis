import React, { useState, useEffect } from 'react';
import { Card } from 'primereact/card';
import { ProgressSpinner } from 'primereact/progressspinner';
import { Message } from 'primereact/message';
import { getDashboardData } from '../services/api';

const Dashboard = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dashboardData, setDashboardData] = useState(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        const data = await getDashboardData();
        setDashboardData(data);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err);
        setError('Failed to load dashboard data. Please check your API key in settings.');
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value);
  };

  if (loading) {
    return (
      <div className="flex justify-content-center align-items-center" style={{ height: '300px' }}>
        <ProgressSpinner />
        <span className="ml-3">Loading dashboard data...</span>
      </div>
    );
  }

  if (error) {
    return <Message severity="error" text={error} className="w-full" />;
  }

  if (!dashboardData) {
    return <Message severity="info" text="No dashboard data available. Upload some transactions to get started." className="w-full" />;
  }

  // Access summary statistics
  const { summary_stats } = dashboardData;

  return (
    <div className="grid">
      <div className="col-12">
        <h1 className="mb-4">Spending Dashboard</h1>
      </div>

      {/* Summary Stats */}
      <div className="col-12 grid">
        <div className="col-12 md:col-6 lg:col-3">
          <Card className="stat-card">
            <div className="title">Total Income</div>
            <div className="value">{formatCurrency(summary_stats.total_income)}</div>
          </Card>
        </div>
        <div className="col-12 md:col-6 lg:col-3">
          <Card className="stat-card">
            <div className="title">Total Expenses</div>
            <div className="value">{formatCurrency(summary_stats.total_expenses)}</div>
          </Card>
        </div>
        <div className="col-12 md:col-6 lg:col-3">
          <Card className="stat-card">
            <div className="title">Savings</div>
            <div className="value">{formatCurrency(summary_stats.savings)}</div>
          </Card>
        </div>
        <div className="col-12 md:col-6 lg:col-3">
          <Card className="stat-card">
            <div className="title">Savings Rate</div>
            <div className="value">{summary_stats.savings_rate}%</div>
          </Card>
        </div>
      </div>

      {/* Spending by Category */}
      <div className="col-12 md:col-6">
        <div className="chart-container">
          <h3>Spending by Category</h3>
          <div dangerouslySetInnerHTML={{ __html: dashboardData.pie_chart }} />
        </div>
      </div>
      <div className="col-12 md:col-6">
        <div className="chart-container">
          <h3>Monthly Expense Trends</h3>
          <div dangerouslySetInnerHTML={{ __html: dashboardData.bar_chart }} />
        </div>
      </div>

      {/* Forecasting */}
      <div className="col-12">
        <div className="chart-container">
          <div dangerouslySetInnerHTML={{ __html: dashboardData.forecast }} />
        </div>
      </div>

      {/* Income vs Expenses */}
      <div className="col-12">
        <div className="chart-container">
          <div dangerouslySetInnerHTML={{ __html: dashboardData.income_vs_expenses }} />
        </div>
      </div>

      {/* Additional Charts */}
      <div className="col-12 md:col-6">
        <div className="chart-container">
          <div dangerouslySetInnerHTML={{ __html: dashboardData.essential_ratio }} />
        </div>
      </div>
      <div className="col-12 md:col-6">
        <div className="chart-container">
          <div dangerouslySetInnerHTML={{ __html: dashboardData.dining_vs_groceries }} />
        </div>
      </div>

      {/* Transaction Table */}
      <div className="col-12">
        <div className="chart-container">
          <div dangerouslySetInnerHTML={{ __html: dashboardData.transaction_table }} />
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
