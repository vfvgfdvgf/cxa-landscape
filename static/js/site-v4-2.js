(() => {
  "use strict";

  let pageController = null;
  let readingTracker = null;
  let motionCleanup = null;

  const getCookie = (name) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    return parts.length === 2 ? parts.pop().split(";").shift() : "";
  };

  const postForm = async (url, payload, { keepalive = false } = {}) => {
    const response = await fetch(url, {
      method: "POST",
      body: payload,
      headers: { "X-CSRFToken": getCookie("csrftoken") },
      credentials: "same-origin",
      keepalive,
    });
    let result = {};
    try {
      result = await response.json();
    } catch (_error) {
      result = { ok: response.ok };
    }
    if (!response.ok || result.ok === false) {
      const error = new Error(result.error || "request_failed");
      error.response = response;
      throw error;
    }
    return result;
  };

  const getAttribution = () => {
    const current = new URLSearchParams(window.location.search);
    const keys = ["utm_source", "utm_medium", "utm_campaign"];
    let stored = {};
    try { stored = JSON.parse(sessionStorage.getItem("siteAttribution") || "{}"); } catch (_error) {}
    keys.forEach((key) => {
      const value = (current.get(key) || stored[key] || "").slice(0, key === "utm_campaign" ? 160 : 120);
      if (value) stored[key] = value;
    });
    try { sessionStorage.setItem("siteAttribution", JSON.stringify(stored)); } catch (_error) {}
    return stored;
  };

  const appendAttribution = (payload) => {
    const attribution = getAttribution();
    ["utm_source", "utm_medium", "utm_campaign"].forEach((key) => payload.set(key, attribution[key] || ""));
  };

  const captureLead = (form, data) => {
    if (!form.dataset.leadUrl) return Promise.resolve({ ok: true });
    const payload = new FormData();
    ["name", "phone", "city", "district", "service", "details", "website"].forEach((key) => {
      payload.set(key, data.get(key) || "");
    });
    payload.set("page_url", window.location.href);
    appendAttribution(payload);
    return postForm(form.dataset.leadUrl, payload);
  };

  const trackConversion = (eventType, label = "", extra = {}) => {
    const trackUrl = document.body.dataset.trackUrl;
    if (!trackUrl) return Promise.resolve({ ok: true });
    const payload = new FormData();
    payload.set("event_type", eventType);
    payload.set("label", label);
    payload.set("page_url", window.location.href);
    Object.entries(extra).forEach(([key, value]) => payload.set(key, value || ""));
    appendAttribution(payload);
    return postForm(trackUrl, payload, { keepalive: true }).catch(() => ({ ok: false }));
  };

  const setFormState = (form, message, type = "info") => {
    let status = form.querySelector("[data-form-status]");
    if (!status) {
      status = document.createElement("p");
      status.dataset.formStatus = "";
      status.className = "form-status";
      status.setAttribute("role", "status");
      form.append(status);
    }
    status.dataset.type = type;
    status.textContent = message;
  };

  const boundEvents = new WeakMap();
  const bindOnce = (element, eventName, handler, key = eventName, options) => {
    const keys = boundEvents.get(element) || new Set();
    const marker = `${eventName}:${key}`;
    if (keys.has(marker)) return;
    keys.add(marker);
    boundEvents.set(element, keys);
    element.addEventListener(eventName, handler, options);
  };

  const initHeader = () => {
    const menuOverlay = document.querySelector("[data-menu-overlay]");
    const searchOverlay = document.querySelector("[data-search-overlay]");
    const menuButton = document.querySelector("[data-open-menu]");
    const searchInput = document.querySelector("#global-site-search");
    let lastFocused = null;

    const getFocusable = (overlay) => [...overlay.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])')];
    const closeAll = ({ restoreFocus = true } = {}) => {
      [menuOverlay, searchOverlay].forEach((overlay) => {
        if (overlay) overlay.hidden = true;
      });
      document.body.classList.remove("shell-overlay-open");
      menuButton?.setAttribute("aria-expanded", "false");
      if (restoreFocus) lastFocused?.focus?.();
    };
    const openOverlay = (overlay, focusTarget = null) => {
      if (!overlay) return;
      lastFocused = document.activeElement;
      closeAll({ restoreFocus: false });
      overlay.hidden = false;
      document.body.classList.add("shell-overlay-open");
      menuButton?.setAttribute("aria-expanded", String(overlay === menuOverlay));
      window.requestAnimationFrame(() => (focusTarget || getFocusable(overlay)[0])?.focus?.());
    };

    document.querySelectorAll("[data-open-menu]").forEach((button) => bindOnce(button, "click", () => openOverlay(menuOverlay), "shellMenu"));
    document.querySelectorAll("[data-open-search]").forEach((button) => bindOnce(button, "click", () => openOverlay(searchOverlay, searchInput), "shellSearch"));
    document.querySelectorAll("[data-close-overlay]").forEach((button) => bindOnce(button, "click", () => closeAll(), "shellClose"));
    document.querySelectorAll("[data-switch-search]").forEach((button) => bindOnce(button, "click", () => openOverlay(searchOverlay, searchInput), "shellSwitch"));

    [menuOverlay, searchOverlay].forEach((overlay) => {
      if (!overlay) return;
      bindOnce(overlay, "keydown", (event) => {
        if (event.key === "Escape") return closeAll();
        if (event.key !== "Tab") return;
        const items = getFocusable(overlay);
        if (!items.length) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }, "shellTrap");
      bindOnce(overlay, "click", (event) => {
        if (event.target.closest("a[href]")) closeAll({ restoreFocus: false });
      }, "shellLink");
    });

    window.closeSiteMenu = () => closeAll({ restoreFocus: false });
  };

  const initReveal = (signal) => {
    const elements = document.querySelectorAll("#swup .reveal:not(.visible)");
    if (!elements.length) return;
    if (!("IntersectionObserver" in window) || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      elements.forEach((element) => element.classList.add("visible"));
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px" }
    );
    elements.forEach((element) => observer.observe(element));
    signal.addEventListener("abort", () => observer.disconnect(), { once: true });
  };

  const openWhatsAppAfterSave = async (form, data, message) => {
    const popup = window.open("about:blank", "_blank");
    const button = form.querySelector('button[type="submit"]');
    if (button) button.disabled = true;
    setFormState(form, "جاري تجهيز طلبك…");
    try {
      await captureLead(form, data);
      await trackConversion("whatsapp", form.classList.contains("conversion-mini-form") ? "quick-bar" : "quote-form", {
        city: data.get("city"),
        service: data.get("service"),
      });
      setFormState(form, "تم حفظ الطلب، جاري فتح واتساب.", "success");
    } catch (error) {
      const text = error.message === "invalid_phone"
        ? "رقم الجوال غير صحيح. عدله ثم حاول مرة ثانية."
        : "تعذر حفظ الطلب مؤقتًا، لكن تقدر تكمل عبر واتساب.";
      setFormState(form, text, error.message === "invalid_phone" ? "error" : "warning");
      if (error.message === "invalid_phone") {
        if (popup) popup.close();
        if (button) button.disabled = false;
        return;
      }
    }
    const url = `${form.dataset.whatsapp}?text=${encodeURIComponent(message)}`;
    if (popup) popup.location.href = url;
    else window.location.href = url;
    if (button) button.disabled = false;
  };

  const initQuoteForms = () => {
    document.querySelectorAll(".quote-form[data-whatsapp]").forEach((form) => {
      bindOnce(form, "submit", async (event) => {
        event.preventDefault();
        const data = new FormData(form);
        const message = [
          "مرحبًا، أريد عرض سعر",
          `الاسم: ${data.get("name") || "-"}`,
          `الجوال: ${data.get("phone") || "-"}`,
          `المدينة: ${data.get("city") || "-"}`,
          `الحي: ${data.get("district") || "-"}`,
          `الخدمة: ${data.get("service") || form.dataset.defaultService || "-"}`,
          `التفاصيل: ${data.get("details") || "-"}`,
          `الصفحة: ${window.location.href}`,
        ].join("\n");
        await openWhatsAppAfterSave(form, data, message);
      }, "quoteSubmit");
    });

    document.querySelectorAll(".conversion-mini-form[data-whatsapp]").forEach((form) => {
      bindOnce(form, "submit", async (event) => {
        event.preventDefault();
        const data = new FormData(form);
        const message = [
          "مرحبًا، أريد عرض سعر سريع",
          `المدينة: ${data.get("city") || "-"}`,
          `الحي: ${data.get("district") || "-"}`,
          `الخدمة: ${data.get("service") || "طلب خدمة"}`,
          `الصفحة: ${window.location.href}`,
        ].join("\n");
        await openWhatsAppAfterSave(form, data, message);
      }, "quickSubmit");
    });
  };


  const initLocationSelectors = () => {
    const dataNode = document.querySelector("#location-options-data");
    let locations = [];
    if (dataNode) {
      try { locations = JSON.parse(dataNode.textContent || "[]"); } catch (_error) { locations = []; }
    }
    document.querySelectorAll("[data-location-city]").forEach((citySelect) => {
      const form = citySelect.closest("form");
      const districtSelect = form?.querySelector("[data-location-district]");
      if (!districtSelect) return;
      const update = () => {
        const city = locations.find((item) => String(item.name) === String(citySelect.value));
        const current = districtSelect.value;
        districtSelect.innerHTML = '<option value="">اختر الحي (اختياري)</option>';
        (city?.districts || []).forEach((district) => {
          const option = document.createElement("option");
          option.value = district.name;
          option.textContent = district.name;
          districtSelect.append(option);
        });
        districtSelect.disabled = !city;
        if ([...districtSelect.options].some((option) => option.value === current)) districtSelect.value = current;
      };
      bindOnce(citySelect, "change", update, "locationCity");
      update();
    });
  };

  const initCalculator = () => {
    document.querySelectorAll("#swup [data-cost-calculator]").forEach((form) => {
      const minTarget = form.querySelector("[data-calc-min]") || document.querySelector("[data-calc-min]");
      const maxTarget = form.querySelector("[data-calc-max]") || document.querySelector("[data-calc-max]");
      const factors = { basic: 0.85, standard: 1, premium: 1.35 };
      const format = (value) => Math.round(value).toLocaleString("ar-SA");
      const update = () => {
        const data = new FormData(form);
        const area = Math.max(10, Number(data.get("area") || 100));
        const factor = factors[data.get("level")] || 1;
        if (minTarget) minTarget.textContent = format(area * Number(form.dataset.minRate || 180) * factor);
        if (maxTarget) maxTarget.textContent = format(area * Number(form.dataset.maxRate || 360) * factor);
      };
      bindOnce(form, "input", update, "calculatorInput");
      bindOnce(form, "change", update, "calculatorChange");
      update();
    });
  };

  const initCopyButtons = () => {
    document.querySelectorAll("#swup [data-copy-link]").forEach((button) => {
      bindOnce(button, "click", async () => {
        try {
          await navigator.clipboard.writeText(button.dataset.copyLink || window.location.href);
          button.textContent = "تم النسخ";
        } catch (_error) {
          button.textContent = "تعذر النسخ";
        }
      }, "copy");
    });
  };

  const initBeforeAfter = () => {
    document.querySelectorAll("#swup [data-before-after]").forEach((widget) => {
      const range = widget.querySelector("[data-before-range]");
      const layer = widget.querySelector("[data-before-layer]");
      const divider = widget.querySelector("[data-before-divider]");
      if (!range || !layer || !divider) return;
      const update = () => {
        const value = `${range.value}%`;
        layer.style.width = value;
        divider.style.insetInlineStart = value;
      };
      bindOnce(range, "input", update, "beforeAfter");
      update();
    });
  };

  const stopReadingTracker = () => {
    if (!readingTracker) return;
    readingTracker.send();
    readingTracker.cleanup();
    readingTracker = null;
  };

  const initReadingTracker = (signal) => {
    stopReadingTracker();
    const target = document.querySelector("#swup [data-reading-target]");
    if (!target?.dataset.trackUrl) return;
    const startedAt = Date.now();
    const progressBar = document.querySelector("#swup [data-reading-progress-bar]");
    let sent = false;

    const update = () => {
      if (!progressBar) return;
      const top = target.getBoundingClientRect().top + window.scrollY;
      const total = Math.max(1, target.offsetHeight - window.innerHeight);
      const consumed = Math.min(total, Math.max(0, window.scrollY - top));
      progressBar.style.width = `${Math.max(0, Math.min(100, (consumed / total) * 100))}%`;
    };

    const send = () => {
      if (sent) return;
      sent = true;
      const seconds = Math.min(900, Math.round((Date.now() - startedAt) / 1000));
      if (seconds < 4) return;
      const payload = new FormData();
      payload.set("seconds", String(seconds));
      postForm(target.dataset.trackUrl, payload, { keepalive: true }).catch(() => {});
    };

    window.addEventListener("scroll", update, { passive: true, signal });
    window.addEventListener("resize", update, { signal });
    window.addEventListener("pagehide", send, { signal });
    update();
    readingTracker = { send, cleanup: () => {} };
  };

  const initMotionSections = (signal) => {
    motionCleanup?.();
    motionCleanup = null;
    const projectPanels = [...document.querySelectorAll("[data-project-panel]")];
    const serviceSection = document.querySelector("[data-services-showcase]");
    const serviceStage = document.querySelector("[data-services-stage]");
    const serviceTrack = document.querySelector("[data-services-track]");
    if (!projectPanels.length && !serviceTrack) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!window.gsap || !window.ScrollTrigger || reduced) return;
    const { gsap, ScrollTrigger } = window;
    gsap.registerPlugin(ScrollTrigger);
    const media = gsap.matchMedia();
    const context = gsap.context(() => {
      projectPanels.slice(0, -1).forEach((panel, index) => {
        const next = projectPanels[index + 1];
        gsap.to(panel, {
          scale: 0.88,
          opacity: 0.38,
          filter: "blur(3px)",
          ease: "none",
          scrollTrigger: {
            trigger: next,
            start: "top 92%",
            end: "top 16%",
            scrub: 0.65,
            invalidateOnRefresh: true,
          },
        });
      });

      if (serviceSection && serviceStage && serviceTrack) {
        media.add("(min-width: 901px)", () => {
          serviceSection.classList.add("is-gsap-ready");
          const getDistance = () => Math.max(0, serviceTrack.scrollWidth - window.innerWidth);
          const tween = gsap.to(serviceTrack, {
            x: () => -getDistance(),
            ease: "none",
            scrollTrigger: {
              trigger: serviceStage,
              start: "top 96px",
              end: () => `+=${Math.max(getDistance(), window.innerWidth * 1.4)}`,
              pin: true,
              scrub: 0.8,
              anticipatePin: 1,
              invalidateOnRefresh: true,
            },
          });
          return () => {
            tween.scrollTrigger?.kill();
            tween.kill();
            serviceSection.classList.remove("is-gsap-ready");
            gsap.set(serviceTrack, { clearProps: "transform" });
          };
        });
      }
    }, document.querySelector("#swup") || document.body);

    const refresh = () => ScrollTrigger.refresh();
    window.setTimeout(refresh, 80);
    document.querySelectorAll("#swup img").forEach((image) => {
      if (!image.complete) image.addEventListener("load", refresh, { once: true, signal });
    });
    motionCleanup = () => {
      media.revert();
      context.revert();
      serviceSection?.classList.remove("is-gsap-ready");
      if (serviceTrack) gsap.set(serviceTrack, { clearProps: "transform" });
    };
    signal.addEventListener("abort", () => motionCleanup?.(), { once: true });
  };

  const getNavigationKey = () => {
    const path = window.location.pathname.replace(/\/$/, "") || "/";
    if (path === "/") return "home";
    if (/^\/portfolio(?:\/|$)/.test(path)) return "portfolio";
    if (/^\/services(?:\/|$)/.test(path)) return "services";
    if (/^\/(?:cities|archive\/cities)(?:\/|$)/.test(path)) return "cities";
    if (/^\/[^/]+\/(?:districts|services)(?:\/|$)/.test(path)) return "cities";
    if (/^\/(?:blog|category|tag)(?:\/|$)/.test(path)) return "blog";
    if (/^\/about(?:\/|$)/.test(path)) return "about";
    if (/^\/contact(?:\/|$)/.test(path)) return "contact";
    const parts = path.split("/").filter(Boolean);
    if (parts.includes("districts")) return "cities";
    try {
      const locations = JSON.parse(document.querySelector("#location-options-data")?.textContent || "[]");
      if (parts[0] && locations.some((city) => city.slug === parts[0])) return "cities";
    } catch (_error) {}
    return "";
  };

  const updateActiveNavigation = () => {
    const currentKey = getNavigationKey();
    document.querySelectorAll("[data-nav-key]").forEach((link) => {
      const active = link.dataset.navKey === currentKey;
      link.classList.toggle("active", active);
      if (active) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
  };

  const initPage = () => {
    if (pageController) pageController.abort();
    pageController = new AbortController();
    const { signal } = pageController;
    initReveal(signal);
    initQuoteForms();
    initLocationSelectors();
    initCalculator();
    initCopyButtons();
    initBeforeAfter();
    initReadingTracker(signal);
    initMotionSections(signal);
    updateActiveNavigation();
    getAttribution();
    const content = document.querySelector("#content");
    if (content?.dataset.themeVars) document.body.setAttribute("style", content.dataset.themeVars);
    document.querySelectorAll("#swup img:not([decoding])").forEach((image) => image.setAttribute("decoding", "async"));
  };

  const initExitModal = () => {
    const modal = document.querySelector("[data-exit-modal]");
    if (!modal || modal.dataset.initialized) return;
    modal.dataset.initialized = "1";
    let previousFocus = null;

    const focusable = () => [...modal.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')];
    const close = () => {
      modal.hidden = true;
      previousFocus?.focus?.();
    };
    const open = () => {
      if (sessionStorage.getItem("exitIntentShown")) return;
      sessionStorage.setItem("exitIntentShown", "1");
      previousFocus = document.activeElement;
      modal.hidden = false;
      focusable()[0]?.focus();
      trackConversion("exit_intent", "shown");
    };

    modal.querySelectorAll("[data-exit-close]").forEach((element) => bindOnce(element, "click", close, "exitClose"));
    bindOnce(modal, "keydown", (event) => {
      if (event.key === "Escape") close();
      if (event.key !== "Tab") return;
      const items = focusable();
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }, "exitKeyboard");

    document.addEventListener("mouseleave", (event) => {
      if (event.clientY <= 0) open();
    });
    window.setTimeout(() => {
      if (window.innerWidth <= 720 && window.scrollY > 600) open();
    }, 18000);
  };

  const initDelegatedTracking = () => {
    if (document.documentElement.dataset.trackingBound) return;
    document.documentElement.dataset.trackingBound = "1";
    document.addEventListener("click", (event) => {
      const link = event.target.closest("a[href]");
      if (!link) return;
      if (link.href.startsWith("https://wa.me") || link.href.includes("api.whatsapp.com")) {
        trackConversion("whatsapp", link.textContent.trim().slice(0, 160));
      } else if (link.href.startsWith("tel:")) {
        trackConversion("call", link.textContent.trim().slice(0, 160));
      }
    });
  };

  const initFastNavigation = () => {
    if (window.siteNavigator || !("fetch" in window) || !("pushState" in history)) return;

    const cache = new Map();
    const inflight = new Map();
    const maxCacheEntries = 24;
    const cacheLifetime = 5 * 60 * 1000;
    let activeRequest = null;
    let navigationId = 0;

    history.scrollRestoration = "manual";

    const normalizeUrl = (value) => {
      const url = new URL(value, window.location.href);
      url.hash = "";
      return url.href;
    };

    const isEligibleLink = (link, event = null) => {
      if (!(link instanceof HTMLAnchorElement) || !link.href) return false;
      if (event && (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey)) return false;
      if (link.hasAttribute("download") || link.target === "_blank" || link.closest("[data-no-fast-nav], [data-no-swup]")) return false;
      const raw = link.getAttribute("href") || "";
      if (!raw || raw.startsWith("#") || /^(?:mailto|tel|javascript):/i.test(raw)) return false;
      const url = new URL(link.href, window.location.href);
      if (url.origin !== window.location.origin) return false;
      if (/^\/(?:admin|media|static)(?:\/|$)/.test(url.pathname)) return false;
      if (url.pathname === window.location.pathname && url.search === window.location.search && url.hash) return false;
      return true;
    };

    const setNavigationState = (isLoading, hasError = false) => {
      document.documentElement.classList.toggle("site-is-navigating", isLoading);
      document.documentElement.classList.toggle("site-nav-error", hasError);
      document.querySelector("#swup")?.setAttribute("aria-busy", String(isLoading));
      if (!isLoading && hasError) window.setTimeout(() => document.documentElement.classList.remove("site-nav-error"), 900);
    };

    const trimCache = () => {
      while (cache.size > maxCacheEntries) cache.delete(cache.keys().next().value);
    };

    const fetchPage = async (url, { signal, useCache = true } = {}) => {
      const key = normalizeUrl(url);
      const cached = cache.get(key);
      if (useCache && cached && Date.now() - cached.cachedAt < cacheLifetime) return cached;
      if (inflight.has(key)) return inflight.get(key);

      const request = (async () => {
        const controller = new AbortController();
        const timeout = window.setTimeout(() => controller.abort("navigation_timeout"), 12000);
        if (signal) signal.addEventListener("abort", () => controller.abort(), { once: true });
        try {
          const response = await fetch(key, {
            method: "GET",
            credentials: "same-origin",
            redirect: "follow",
            headers: {
              "X-Requested-With": "FastNavigation",
              "Accept": "text/html, application/xhtml+xml",
            },
            signal: controller.signal,
          });
          if (!response.ok) throw new Error(`navigation_http_${response.status}`);
          const type = response.headers.get("content-type") || "";
          if (!type.includes("text/html")) throw new Error("navigation_not_html");
          const html = await response.text();
          if (!html.includes('id="swup"')) throw new Error("navigation_container_missing");
          const page = { html, url: response.url || key, cachedAt: Date.now() };
          const cacheControl = response.headers.get("cache-control") || "";
          if (!/no-store/i.test(cacheControl)) {
            cache.set(key, page);
            cache.set(normalizeUrl(page.url), page);
            trimCache();
          }
          return page;
        } finally {
          window.clearTimeout(timeout);
          inflight.delete(key);
        }
      })();
      inflight.set(key, request);
      return request;
    };

    const syncHead = (nextDocument) => {
      document.title = nextDocument.title || document.title;
      const selectors = [
        'meta[name="description"]', 'meta[name="keywords"]', 'meta[name="robots"]',
        'meta[name="theme-color"]', 'meta[property^="og:"]', 'meta[name^="twitter:"]',
        'link[rel="canonical"]', 'link[rel="prev"]', 'link[rel="next"]',
        'link[rel="alternate"][hreflang]', 'link[rel="preload"][as="image"]', 'script[type="application/ld+json"]'
      ];
      selectors.forEach((selector) => {
        document.head.querySelectorAll(selector).forEach((node) => node.remove());
        nextDocument.head.querySelectorAll(selector).forEach((node) => document.head.append(node.cloneNode(true)));
      });
      document.documentElement.lang = nextDocument.documentElement.lang || "ar";
      document.documentElement.dir = nextDocument.documentElement.dir || "rtl";
      document.documentElement.className = nextDocument.documentElement.className;
      document.body.className = nextDocument.body.className;
      const nextStyle = nextDocument.body.getAttribute("style");
      if (nextStyle) document.body.setAttribute("style", nextStyle);
      else document.body.removeAttribute("style");
      [...document.body.attributes]
        .filter((attribute) => attribute.name.startsWith("data-"))
        .forEach((attribute) => document.body.removeAttribute(attribute.name));
      [...nextDocument.body.attributes]
        .filter((attribute) => attribute.name.startsWith("data-"))
        .forEach((attribute) => document.body.setAttribute(attribute.name, attribute.value));
    };

    const scrollToHash = (hash, behavior = "auto") => {
      if (!hash) return false;
      let id = hash.replace(/^#/, "");
      try { id = decodeURIComponent(id); } catch (_error) {}
      const escaped = window.CSS?.escape ? window.CSS.escape(id) : id.replace(/(["\\])/g, "\\$1");
      const target = document.getElementById(id) || document.querySelector(`[name="${escaped}"]`);
      if (!target) return false;
      target.scrollIntoView({ behavior, block: "start" });
      return true;
    };

    const replacePage = async (page, { push = true, restoreScroll = null } = {}) => {
      const parser = new DOMParser();
      const nextDocument = parser.parseFromString(page.html, "text/html");
      const nextMain = nextDocument.querySelector("#swup");
      const currentMain = document.querySelector("#swup");
      if (!nextMain || !currentMain) throw new Error("navigation_container_missing");

      const apply = () => {
        document.dispatchEvent(new CustomEvent("site:before-page-swap"));
        motionCleanup?.();
        pageController?.abort();
        stopReadingTracker();
        syncHead(nextDocument);
        currentMain.replaceWith(document.importNode(nextMain, true));
        const nextUrl = new URL(page.url, window.location.origin);
        if (push) history.pushState({ fastNav: true, scrollY: 0 }, "", `${nextUrl.pathname}${nextUrl.search}${nextUrl.hash}`);
        initPage();
        window.closeSiteMenu?.();
        if (typeof restoreScroll === "number") window.scrollTo({ top: restoreScroll, behavior: "auto" });
        else if (nextUrl.hash && scrollToHash(nextUrl.hash, "auto")) {}
        else window.scrollTo({ top: 0, behavior: "auto" });
        document.querySelector("#swup")?.focus({ preventScroll: true });
        document.dispatchEvent(new CustomEvent("site:page-view", { detail: { url: nextUrl.href } }));
      };

      if (document.startViewTransition && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        await document.startViewTransition(apply).finished;
      } else {
        apply();
      }
    };

    const navigate = async (url, options = {}) => {
      const target = new URL(url, window.location.href);
      if (target.origin !== window.location.origin) return window.location.assign(target.href);
      if (target.pathname === window.location.pathname && target.search === window.location.search) {
        if (target.hash) {
          scrollToHash(target.hash, "smooth");
          history.pushState({ fastNav: true, scrollY: window.scrollY }, "", target.href);
        } else {
          window.scrollTo({ top: 0, behavior: "smooth" });
        }
        return;
      }

      const id = ++navigationId;
      if (options.push !== false) {
        history.replaceState({ ...(history.state || {}), fastNav: true, scrollY: window.scrollY }, "", window.location.href);
      }
      activeRequest?.abort();
      activeRequest = new AbortController();
      setNavigationState(true);
      try {
        const page = await fetchPage(target.href, { signal: activeRequest.signal });
        if (id !== navigationId) return;
        const finalUrl = new URL(page.url, window.location.origin);
        if (target.hash) finalUrl.hash = target.hash;
        await replacePage({ ...page, url: finalUrl.href }, options);
        setNavigationState(false);
      } catch (error) {
        if (error?.name === "AbortError" && id !== navigationId) return;
        console.error("Fast navigation failed; using a normal page load.", error);
        setNavigationState(false, true);
        window.location.assign(target.href);
      } finally {
        if (id === navigationId) activeRequest = null;
      }
    };

    const prefetch = (href) => {
      if (!href || navigator.connection?.saveData) return;
      const run = () => fetchPage(href).catch(() => {});
      if ("requestIdleCallback" in window) requestIdleCallback(run, { timeout: 1200 });
      else window.setTimeout(run, 80);
    };

    document.addEventListener("click", (event) => {
      const link = event.target.closest?.("a[href]");
      if (!isEligibleLink(link, event)) return;
      event.preventDefault();
      navigate(link.href);
    });

    document.addEventListener("submit", (event) => {
      const form = event.target.closest?.('form[data-swup-form], form[data-fast-nav-form]');
      if (!form || event.defaultPrevented || String(form.method || "get").toLowerCase() !== "get") return;
      event.preventDefault();
      const url = new URL(form.action || window.location.href, window.location.origin);
      url.search = "";
      new FormData(form).forEach((value, key) => {
        const text = String(value).trim();
        if (text) url.searchParams.append(key, text);
      });
      navigate(url.href);
    });

    document.addEventListener("pointerover", (event) => {
      const link = event.target.closest?.("a[href]");
      if (isEligibleLink(link)) prefetch(link.href);
    }, { passive: true });
    document.addEventListener("focusin", (event) => {
      const link = event.target.closest?.("a[href]");
      if (isEligibleLink(link)) prefetch(link.href);
    });

    window.addEventListener("popstate", (event) => {
      navigate(window.location.href, { push: false, restoreScroll: event.state?.scrollY ?? 0 });
    });
    window.addEventListener("pageshow", (event) => {
      if (event.persisted) initPage();
    });

    let scrollStateFrame = 0;
    const persistScrollState = () => {
      scrollStateFrame = 0;
      history.replaceState({ ...(history.state || {}), fastNav: true, scrollY: window.scrollY }, "", window.location.href);
    };
    window.addEventListener("scroll", () => {
      if (!scrollStateFrame) scrollStateFrame = window.requestAnimationFrame(persistScrollState);
    }, { passive: true });
    window.addEventListener("pagehide", persistScrollState);

    history.replaceState({ ...(history.state || {}), fastNav: true, scrollY: window.scrollY }, "", window.location.href);
    window.siteNavigator = { navigate, prefetch, cache };
  };

  document.addEventListener("DOMContentLoaded", () => {
    initHeader();
    initExitModal();
    initDelegatedTracking();
    initPage();
    initFastNavigation();
  });
})();
