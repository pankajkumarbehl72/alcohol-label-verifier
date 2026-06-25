const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function verifyLabel(formValues, file) {
  const formData = new FormData();

  formData.append("file", file);
  formData.append("brand_name", formValues.brand_name);
  formData.append("class_type", formValues.class_type);
  formData.append("alcohol_content", formValues.alcohol_content);
  formData.append("net_contents", formValues.net_contents);

  if (formValues.producer_name_address) {
    formData.append("producer_name_address", formValues.producer_name_address);
  }

  if (formValues.country_of_origin) {
    formData.append("country_of_origin", formValues.country_of_origin);
  }

  const response = await fetch(`${API_BASE_URL}/api/verify`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Verification failed.");
  }

  return response.json();
}
