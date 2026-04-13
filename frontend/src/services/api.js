import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
});

export async function processFolder(folderPath, overwriteExisting = false) {
  const { data } = await api.post("/api/upload/process-folder", {
    folder_path: folderPath,
    overwrite_existing: overwriteExisting,
  });
  return data;
}

export async function fetchCandidates() {
  const { data } = await api.get("/api/candidates/");
  return data;
}

export async function fetchCandidateDetail(id) {
  const { data } = await api.get(`/api/candidates/${id}`);
  return data;
}

export async function fetchEmailDraft(id) {
  const { data } = await api.get(`/api/analysis/email-draft/${id}`);
  return data;
}

export async function fetchCandidateSummary(id) {
  const { data } = await api.get(`/api/analysis/summary/${id}`);
  return data;
}

export async function fetchRoleAlignment(id, jobDescription) {
  const { data } = await api.post(`/api/analysis/role-alignment/${id}`, {
    job_description: jobDescription,
  });
  return data;
}

export async function fetchProcessingStatus(folderPath) {
  const { data } = await api.get("/api/upload/status", {
    params: { folder_path: folderPath },
  });
  return data;
}
