import React, { useState } from 'react';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8001';

function App() {
  const [productName, setProductName] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch(`${API_URL}/compare/${encodeURIComponent(productName)}`);
      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError('Error fetching data. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Price Comparison Tool</h1>
        <form onSubmit={handleSearch} className="search-form">
          <input
            type="text"
            value={productName}
            onChange={(e) => setProductName(e.target.value)}
            placeholder="Enter product name..."
            className="search-input"
          />
          <button type="submit" className="search-button" disabled={loading}>
            {loading ? 'Searching...' : 'Compare Prices'}
          </button>
        </form>

        {error && <div className="error-message">{error}</div>}

        <div className="results-container">
          {results.map((result, index) => (
            <div key={index} className="result-card">
              <h2>{result.platform}</h2>
              <div className="price">₹{result.price.toLocaleString()}</div>
              <a 
                href={result.link} 
                target="_blank" 
                rel="noopener noreferrer"
                className="product-link"
              >
                View Product
              </a>
            </div>
          ))}
        </div>
      </header>
    </div>
  );
}

export default App;
