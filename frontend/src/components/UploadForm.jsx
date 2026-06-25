import { useState } from "react";

const initialValues = {
  brand_name: "OLD TOM DISTILLERY",
  class_type: "Kentucky Straight Bourbon Whiskey",
  alcohol_content: "45% Alc./Vol. (90 Proof)",
  net_contents: "750 mL",
  producer_name_address: "",
  country_of_origin: "",
};

export default function UploadForm({ onVerify, isLoading }) {
  const [formValues, setFormValues] = useState(initialValues);
  const [file, setFile] = useState(null);

  function updateField(event) {
    const { name, value } = event.target;
    setFormValues((previous) => ({
      ...previous,
      [name]: value,
    }));
  }

  function handleSubmit(event) {
    event.preventDefault();

    if (!file) {
      alert("Please upload a label image first.");
      return;
    }

    onVerify(formValues, file);
  }

  return (
    <form className="card form-card" onSubmit={handleSubmit}>
      <h2>Application Fields</h2>
      <p className="helper">
        These are the values from the label application. The app checks whether the label artwork matches them.
      </p>

      <label>
        Brand Name *
        <input
          name="brand_name"
          value={formValues.brand_name}
          onChange={updateField}
          required
        />
      </label>

      <label>
        Class / Type *
        <input
          name="class_type"
          value={formValues.class_type}
          onChange={updateField}
          required
        />
      </label>

      <label>
        Alcohol Content *
        <input
          name="alcohol_content"
          value={formValues.alcohol_content}
          onChange={updateField}
          required
        />
      </label>

      <label>
        Net Contents *
        <input
          name="net_contents"
          value={formValues.net_contents}
          onChange={updateField}
          required
        />
      </label>

      <label>
        Producer / Bottler Name and Address
        <input
          name="producer_name_address"
          value={formValues.producer_name_address}
          onChange={updateField}
          placeholder="Optional for prototype"
        />
      </label>

      <label>
        Country of Origin
        <input
          name="country_of_origin"
          value={formValues.country_of_origin}
          onChange={updateField}
          placeholder="Optional"
        />
      </label>

      <label>
        Label Image *
        <input
          type="file"
          accept="image/png,image/jpeg,image/jpg"
          onChange={(event) => setFile(event.target.files?.[0] || null)}
          required
        />
      </label>

      <button type="submit" disabled={isLoading}>
        {isLoading ? "Checking Label..." : "Verify Label"}
      </button>
    </form>
  );
}
