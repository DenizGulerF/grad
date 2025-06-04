import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import './style.css';
import './home.css';
import logo from '../assets/images/logo.png';
import profileImg from '../assets/images/21.png';

const Home = () => {
  const [url, setUrl] = useState('');
  const [username, setUsername] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef(null);
  const profileToggleRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    console.log("Home page loaded, checking auth_token...");
    const token = localStorage.getItem('auth_token');
    console.log("DOMContentLoaded check - auth_token:", token);
    
    if (!token) {
      console.warn("No auth token found, redirecting to login");
      navigate('/');
      return;
    }

    // Close dropdown when clicking outside
    const handleClickOutside = (event) => {
      if (
        dropdownRef.current && 
        profileToggleRef.current && 
        !profileToggleRef.current.contains(event.target)
      ) {
        setShowDropdown(false);
      }
    };
    
    window.addEventListener('click', handleClickOutside);
    
    // Fetch user profile
    const fetchUserProfile = async () => {
      try {
        const API_BASE = 'http://127.0.0.1:5000/api';
        const response = await fetch(`${API_BASE}/profile`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!response.ok) {
          throw new Error('Profile fetch failed');
        }
        
        const data = await response.json();
        console.log("Profile data:", data);
        
        if (data.user && data.user.username) {
          setUsername(data.user.username);
        }
      } catch (error) {
        console.error("Error in profile fetch:", error);
      }
    };
    
    fetchUserProfile();
    
    return () => {
      window.removeEventListener('click', handleClickOutside);
    };
  }, [navigate]);

  const handleGoToProduct = () => {
    if (url) {
      localStorage.setItem('productUrl', url);
      console.log("Before navigate to product page, auth_token:", localStorage.getItem('auth_token'));
      
      // Allow localStorage to update before navigation
      setTimeout(() => {
        navigate('/product');
      }, 50);
    }
  };

  const handleLogout = (e) => {
    e.preventDefault();
    localStorage.removeItem('auth_token');
    navigate('/');
  };

  const toggleProfile = () => {
    setShowDropdown(prev => !prev);
  };

  // Handle keypress - allow Enter key to submit
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && url) {
      handleGoToProduct();
    }
  };

  return (
    <div className="home-container">
      {/* Fixed position elements */}
      <button className="save-product-btn" onClick={() => navigate('/saved')}>
        Saved Products
      </button>

      <div 
        className="profile-container" 
        onClick={toggleProfile}
        ref={profileToggleRef}
      >
        <img src={profileImg} alt="Profile" className="profile-img" />
        <i className="fa fa-chevron-down dropdown-icon"></i>
        <div 
          className={`profile-dropdown ${showDropdown ? 'show' : ''}`}
          ref={dropdownRef}
        >
          <button className="dropdown-item" onClick={() => console.log('Profile settings clicked')}>
            Profile Settings
          </button>
          <button className="dropdown-item" onClick={handleLogout}>
            Log Out
          </button>
        </div>
      </div>

      {/* Main content - moved down */}
      <div className="main-container">
        <img src={logo} alt="Logo" className="logo" />
        
        <div className="welcome-message">
          {username ? `Welcome, ${username}!` : 'Welcome to Gravify!'}
        </div>

        <div className="url-input-container">
          <input 
            type="text" 
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Insert the URL" 
            className="url-input"
          />
          <i 
            className="fa fa-arrow-up url-icon" 
            onClick={handleGoToProduct}
          ></i>
        </div>
      </div>
    </div>
  );
};

export default Home;