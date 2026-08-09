(function () {
  const form = document.querySelector("form");
  const contentField = document.getElementById("id_content");
  const excerptField = document.getElementById("id_excerpt");
  const titleField = document.getElementById("id_title");

  if (!form || !contentField) {
    return;
  }

  const storageKey = `blog-draft-${window.location.pathname}`;
  const saveDraft = () => {
    const payload = {
      title: titleField ? titleField.value : "",
      excerpt: excerptField ? excerptField.value : "",
      content: contentField.value,
    };
    localStorage.setItem(storageKey, JSON.stringify(payload));
  };

  const draft = localStorage.getItem(storageKey);
  if (draft && !contentField.value) {
    try {
      const parsed = JSON.parse(draft);
      if (titleField && parsed.title) titleField.value = parsed.title;
      if (excerptField && parsed.excerpt) excerptField.value = parsed.excerpt;
      if (parsed.content) contentField.value = parsed.content;
    } catch (error) {
      localStorage.removeItem(storageKey);
    }
  }

  [titleField, excerptField, contentField].filter(Boolean).forEach((field) => {
    field.addEventListener("input", saveDraft);
  });

  form.addEventListener("submit", () => {
    localStorage.removeItem(storageKey);
  });
})();
