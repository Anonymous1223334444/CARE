
// lib/api.ts

const API_BASE_URL = process.env.NEXT_PUBLIC_DJANGO_API_BASE_URL ? `${process.env.NEXT_PUBLIC_DJANGO_API_BASE_URL}/api` : 'http://localhost:8000/api';

export async function getPatientStats(): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/patients/list/`);
    if (!response.ok) {
      throw new Error('Failed to fetch patient stats');
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching patient stats:', error);
    return { total_count: 0 };
  }
}

export async function getPatients(): Promise<any[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/patients/list/`);
    if (!response.ok) {
      throw new Error('Failed to fetch patients');
    }
    const data = await response.json();
    return data.results || [];
  } catch (error) {
    console.error('Error fetching patients:', error);
    return [];
  }
}

export async function getSessionStats(): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/sessions/stats/`);
    if (!response.ok) {
      throw new Error('Failed to fetch session stats');
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching session stats:', error);
    return {};
  }
}

export async function getDocuments(): Promise<any[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/documents/`);
    if (!response.ok) {
      throw new Error('Failed to fetch documents');
    }
    const data = await response.json();
    return data || [];
  } catch (error) {
    console.error('Error fetching documents:', error);
    return [];
  }
}

export async function getMetricsDashboard(): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/metrics/dashboard/`);
    if (!response.ok) {
      throw new Error('Failed to fetch metrics dashboard');
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching metrics dashboard:', error);
    return {};
  }
}

export async function getBroadcastStats(): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/messaging/broadcast/stats/`);
    if (!response.ok) {
      throw new Error('Failed to fetch broadcast stats');
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching broadcast stats:', error);
    return null;
  }
}
