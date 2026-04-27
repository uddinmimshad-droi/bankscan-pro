import axios from "axios";

const API_BASE_URL = localStorage.getItem("bankscanApiUrl") || import.meta.env.VITE_API_BASE_URL || "https://bankscan-pro.onrender.com";

export const api = axios.create({
  baseURL: API_BASE_URL,
});

export async function uploadPdf(file) {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function getStatus(jobId) {
  const { data } = await api.get(`/status/${jobId}`);
  return data;
}

export async function getPreview(jobId) {
  const { data } = await api.get(`/preview/${jobId}`);
  return data;
}

export function downloadUrl(jobId) {
  return `${API_BASE_URL}/download/${jobId}`;
}

export async function cancelJob(jobId) {
  const { data } = await api.post(`/cancel/${jobId}`);
  return data;
}
