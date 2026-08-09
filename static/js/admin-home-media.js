(() => {
  "use strict";

  const COPY = {
    text: "هذا عنصر نصي؛ استخدم العنوان والوصف والرابط فقط.",
    image: "اختر صورة مرفوعة أو رابط صورة واحد، وأضف وصفًا بديلًا واضحًا.",
    video: "اختر فيديو مرفوعًا أو رابطه، ثم أضف Poster خفيفًا لضمان ظهور جميل قبل التشغيل.",
  };

  const dimRows = (root, selector, dimmed) => {
    root.querySelectorAll(selector).forEach((field) => {
      const row = field.closest(".form-row, .form-group") || field.parentElement;
      row?.classList.toggle("cms-field-dimmed", dimmed);
    });
  };

  const updateMediaType = (select) => {
    const root = select.closest(".inline-related") || select.closest("form") || document;
    const value = select.value || "text";
    let hint = select.parentElement?.querySelector(".cms-media-hint");
    if (!hint) {
      hint = document.createElement("small");
      hint.className = "cms-media-hint";
      select.insertAdjacentElement("afterend", hint);
    }
    hint.textContent = COPY[value] || COPY.text;
    dimRows(root, '[name$="-image"], [name$="-image_url"]', value !== "image");
    dimRows(root, '[name$="-video"], [name$="-video_url"], [name$="-mobile_video"], [name$="-mobile_video_url"], [name$="-poster"], [name$="-poster_url"]', value !== "video");
  };

  const addLocalPreview = (input) => {
    if (input.dataset.cmsPreviewReady || input.type !== "file") return;
    input.dataset.cmsPreviewReady = "true";
    input.addEventListener("change", () => {
      const file = input.files?.[0];
      const row = input.closest(".form-row, .form-group") || input.parentElement;
      row?.querySelector(".cms-local-preview")?.remove();
      if (!file || (!file.type.startsWith("image/") && !file.type.startsWith("video/"))) return;
      const preview = document.createElement(file.type.startsWith("video/") ? "video" : "img");
      preview.className = "cms-local-preview";
      preview.src = URL.createObjectURL(file);
      preview.setAttribute("aria-label", "معاينة قبل الحفظ");
      if (preview instanceof HTMLVideoElement) {
        preview.controls = true;
        preview.muted = true;
      }
      row?.append(preview);
    });
  };

  const init = (root = document) => {
    root.querySelectorAll('select[name="media_type"], select[name$="-media_type"]').forEach((select) => {
      if (!select.dataset.cmsMediaReady) {
        select.dataset.cmsMediaReady = "true";
        select.addEventListener("change", () => updateMediaType(select));
      }
      updateMediaType(select);
    });
    root.querySelectorAll('input[type="file"][name*="image"], input[type="file"][name*="video"], input[type="file"][name*="poster"]').forEach(addLocalPreview);
  };

  document.addEventListener("DOMContentLoaded", () => {
    init();
    document.addEventListener("formset:added", (event) => init(event.target));
  }, { once: true });
})();
