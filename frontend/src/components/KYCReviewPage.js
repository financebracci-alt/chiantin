// KYC Review Status Page - "Application Under Review"
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { NotificationBell } from './Notifications';
import { APP_NAME } from '../config';

export function KYCReviewPage({ user, logout }) {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-white">
      <header className="header-bar">
        <div className="container-main h-full flex justify-between items-center">
          <h1 className="text-lg font-semibold text-gray-900">{APP_NAME}</h1>
          <div className="flex items-center space-x-4">
            <NotificationBell />
            <button onClick={logout} className="text-sm text-gray-600 hover:text-gray-900">Logout</button>
          </div>
        </div>
      </header>

      <div className="container-main py-16">
        <div className="max-w-2xl mx-auto text-center">
          {/* Illustration */}
          <div className="mb-8">
            <div className="w-32 h-32 bg-yellow-100 rounded-full flex items-center justify-center mx-auto">
              <svg className="w-16 h-16 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>

          <h1 className="text-3xl font-bold mb-4">Your application is being reviewed</h1>
          <p className="text-gray-600 mb-8">
            Thank you for submitting your verification. Our team is reviewing your application. 
            This usually takes 1-2 business days.
          </p>

          <div className="card p-6 text-left mb-8">
            <h3 className="font-semibold mb-4">What happens next?</h3>
            <ul className="space-y-3">
              <li className="flex items-start space-x-3">
                <span className="text-red-600 mt-1">1.</span>
                <div>
                  <p className="font-medium">Review process</p>
                  <p className="text-sm text-gray-600">Our team verifies your documents and information</p>
                </div>
              </li>
              <li className="flex items-start space-x-3">
                <span className="text-red-600 mt-1">2.</span>
                <div>
                  <p className="font-medium">Account activation</p>
                  <p className="text-sm text-gray-600">Once approved, your account and IBAN will be activated</p>
                </div>
              </li>
              <li className="flex items-start space-x-3">
                <span className="text-red-600 mt-1">3.</span>
                <div>
                  <p className="font-medium">Full banking access</p>
                  <p className="text-sm text-gray-600">You'll be able to send money, order cards, and use all features</p>
                </div>
              </li>
            </ul>
          </div>

          <button onClick={() => window.location.reload()} className="btn-secondary">
            Check Status
          </button>
        </div>
      </div>
    </div>
  );
}
