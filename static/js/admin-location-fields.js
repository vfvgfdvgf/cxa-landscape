(() => {
  "use strict";

  const pairs = [
    ["id_city", "id_district"],
    ["id_primary_city", "id_primary_district"],
  ];

  const init = async () => {
    const activePairs = pairs
      .map(([cityId, districtId]) => [document.getElementById(cityId), document.getElementById(districtId)])
      .filter(([city, district]) => city && district);
    if (!activePairs.length) return;

    let locations = [];
    try {
      const response = await fetch("/location-options.json", {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) return;
      locations = await response.json();
    } catch (_error) {
      return;
    }

    activePairs.forEach(([citySelect, districtSelect]) => {
      const initialDistrict = String(districtSelect.value || "");
      const updateDistricts = () => {
        const cityId = String(citySelect.value || "");
        const city = locations.find((item) => String(item.id) === cityId);
        const wanted = String(districtSelect.value || initialDistrict || "");
        districtSelect.innerHTML = '<option value="">---------</option>';
        (city?.districts || []).forEach((district) => {
          const option = document.createElement("option");
          option.value = String(district.id);
          option.textContent = district.name;
          if (String(district.id) === wanted) option.selected = true;
          districtSelect.append(option);
        });
        districtSelect.disabled = !city;
      };
      citySelect.addEventListener("change", () => {
        districtSelect.value = "";
        updateDistricts();
      });
      updateDistricts();
    });
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
