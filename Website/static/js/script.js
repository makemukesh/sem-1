/**
 * RainVision — Intelligent Rainfall Prediction & Climate Analytics
 * Vanilla JavaScript Frontend Controller (No React/Node/Tailwind)
 * Integrates directly with Flask REST APIs and Chart.js
 */

(function () {
  "use strict";

  // Application State
  const state = {
    activeSection: "home",
    selectedModel: "ensemble",
    dashboardData: null,
    metricsData: null,
    charts: {},
    explorer: {
      page: 1,
      limit: 20,
      totalPages: 1,
      search: "",
      year: "all",
      rain: "all",
      sortBy: "date",
      sortOrder: "desc"
    }
  };

  // Weather Presets
  const PRESETS = {
    monsoon: { temperature: 28.0, humidity: 92.0, pressure: 998.0, wind_speed: 28.0, previous_rainfall: 45.0 },
    dry: { temperature: 34.0, humidity: 35.0, pressure: 1016.0, wind_speed: 10.0, previous_rainfall: 0.0 },
    premonsoon: { temperature: 31.5, humidity: 78.0, pressure: 1004.0, wind_speed: 18.0, previous_rainfall: 12.0 },
    winter: { temperature: 16.0, humidity: 45.0, pressure: 1018.0, wind_speed: 12.0, previous_rainfall: 0.0 }
  };

  // Validation Bounds
  const BOUNDS = {
    temperature: { min: -10, max: 60, name: "Temperature" },
    humidity: { min: 0, max: 100, name: "Humidity" },
    pressure: { min: 850, max: 1100, name: "Pressure" },
    wind_speed: { min: 0, max: 180, name: "Wind Speed" },
    previous_rainfall: { min: 0, max: 500, name: "Previous Rainfall" }
  };

  // ===================================================================
  // Navigation & Section Router
  // ===================================================================

  function switchSection(targetSection) {
    if (!targetSection) return;
    state.activeSection = targetSection;

    // Update nav links
    document.querySelectorAll(".nav-link").forEach((link) => {
      if (link.dataset.target === targetSection) {
        link.classList.add("active");
      } else {
        link.classList.remove("active");
      }
    });

    // Update section visibility
    document.querySelectorAll(".page-section").forEach((sec) => {
      sec.classList.remove("active");
    });

    const targetEl = document.getElementById(`section-${targetSection}`);
    if (targetEl) {
      targetEl.classList.add("active");
      window.scrollTo({ top: 0, behavior: "smooth" });
    }

    // Close mobile nav if open
    const navMenu = document.getElementById("nav-menu");
    if (navMenu && navMenu.classList.contains("open")) {
      navMenu.classList.remove("open");
    }

    // Trigger lazy section loading
    if (targetSection === "dashboard") {
      loadDashboard();
    } else if (targetSection === "explorer") {
      loadDatasetExplorer();
    } else if (targetSection === "compare") {
      runModelComparison();
    } else if (targetSection === "analytics") {
      loadAnalytics();
    }
  }

  function initNavigation() {
    // Nav menu links
    document.querySelectorAll(".nav-link[data-target]").forEach((link) => {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        switchSection(link.dataset.target);
      });
    });

    // In-page triggers (hero buttons, footer links, etc.)
    document.querySelectorAll(".nav-trigger[data-target]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        switchSection(btn.dataset.target);
      });
    });

    // Mobile Hamburger Toggle
    const mobileToggle = document.getElementById("mobile-toggle");
    const navMenu = document.getElementById("nav-menu");
    if (mobileToggle && navMenu) {
      mobileToggle.addEventListener("click", () => {
        navMenu.classList.toggle("open");
      });
    }

    // Handle initial URL hash if present
    const hash = window.location.hash.replace("#", "").trim();
    if (hash && ["home", "dashboard", "prediction", "compare", "explorer", "analytics", "about"].includes(hash)) {
      switchSection(hash);
    }
  }

  // ===================================================================
  // Toast Notifications
  // ===================================================================

  function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    const icon = type === "error" ? "⚠️" : type === "success" ? "✅" : "ℹ️";
    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(100%)";
      toast.style.transition = "all 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  // ===================================================================
  // Dashboard Section & Charts
  // ===================================================================

  async function loadDashboard() {
    try {
      const res = await fetch("/api/dashboard/summary");
      if (!res.ok) throw new Error("Failed to load dashboard summary");
      const data = await res.json();
      state.dashboardData = data;

      // Update KPIs
      const kpis = data.kpis;
      setText("kpi-records", kpis.total_records.toLocaleString());
      setText("explorer-total-records", kpis.total_records.toLocaleString());
      setText("kpi-avg-rain", kpis.average_historical_rainfall_mm.toFixed(2));
      setText("kpi-max-rain", kpis.max_recorded_rainfall_mm.toFixed(1));
      setText("kpi-min-rain", kpis.min_recorded_rainfall_mm.toFixed(1));
      setText("kpi-models-count", kpis.models_count);

      if (kpis.latest_prediction) {
        setText("kpi-latest-pred", `${kpis.latest_prediction.predicted_rainfall_mm.toFixed(1)} mm`);
        setText("kpi-latest-model", `${kpis.latest_prediction.model} (${kpis.latest_prediction.category})`);
      }

      // Render Charts
      renderHistoricalTrendsChart(data.recent_trends);
      renderDistributionChart(data.rainfall_distribution);
      renderMonthlyBarChart(data.monthly_distribution);
      renderYearlyBarChart(data.yearly_comparison);
    } catch (err) {
      console.error("Dashboard load error:", err);
      showToast("Unable to load dashboard data from server.", "error");
    }
  }

  function destroyChart(chartKey) {
    if (state.charts[chartKey]) {
      state.charts[chartKey].destroy();
      state.charts[chartKey] = null;
    }
  }

  function renderHistoricalTrendsChart(records) {
    if (!window.Chart || !records || !records.length) return;
    destroyChart("historicalTrends");

    const ctx = document.getElementById("chart-historical-trends");
    if (!ctx) return;

    const labels = records.map((r) => r.date.slice(5)); // MM-DD
    const rainfallData = records.map((r) => r.rainfall);
    const humidityData = records.map((r) => r.humidity);

    state.charts.historicalTrends = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Rainfall (mm)",
            data: rainfallData,
            borderColor: "#22D3EE",
            backgroundColor: "rgba(34, 211, 238, 0.15)",
            borderWidth: 2.5,
            fill: true,
            tension: 0.35,
            yAxisID: "y"
          },
          {
            label: "Humidity (%)",
            data: humidityData,
            borderColor: "#94A3B8",
            borderDash: [4, 4],
            borderWidth: 1.5,
            fill: false,
            tension: 0.2,
            yAxisID: "y1"
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { position: "top", labels: { font: { family: "inherit", size: 12 } } },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ${ctx.raw} ${ctx.dataset.yAxisID === "y" ? "mm" : "%"}`
            }
          }
        },
        scales: {
          y: {
            type: "linear",
            display: true,
            position: "left",
            title: { display: true, text: "Rainfall (mm)", font: { size: 11 } },
            grid: { color: "rgba(0, 0, 0, 0.05)" }
          },
          y1: {
            type: "linear",
            display: true,
            position: "right",
            min: 0,
            max: 100,
            title: { display: true, text: "Humidity (%)", font: { size: 11 } },
            grid: { drawOnChartArea: false }
          },
          x: { grid: { display: false } }
        }
      }
    });
  }

  function renderDistributionChart(bins) {
    if (!window.Chart || !bins) return;
    destroyChart("distributionPie");

    const ctx = document.getElementById("chart-distribution-pie");
    if (!ctx) return;

    const labels = bins.map((b) => b.range);
    const dataCounts = bins.map((b) => b.count);

    state.charts.distributionPie = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [
          {
            data: dataCounts,
            backgroundColor: ["#94A3B8", "#60A5FA", "#34D399", "#FBBF24", "#EF4444"],
            borderWidth: 2,
            borderColor: "#FFFFFF"
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom", labels: { font: { size: 11 } } },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.label}: ${ctx.raw.toLocaleString()} days`
            }
          }
        }
      }
    });
  }

  function renderMonthlyBarChart(monthlyData) {
    if (!window.Chart || !monthlyData) return;
    destroyChart("monthlyBar");

    const ctx = document.getElementById("chart-monthly-bar");
    if (!ctx) return;

    const labels = monthlyData.map((m) => m.month);
    const avgData = monthlyData.map((m) => m.average_mm);
    const colors = monthlyData.map((m) => (m.is_monsoon ? "#22D3EE" : "#2563EB"));

    state.charts.monthlyBar = new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Average Daily Rainfall (mm)",
            data: avgData,
            backgroundColor: colors,
            borderRadius: 6
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => `Avg Daily Rain: ${ctx.raw} mm`
            }
          }
        },
        scales: {
          y: {
            title: { display: true, text: "Rainfall (mm)" },
            grid: { color: "rgba(0, 0, 0, 0.05)" }
          },
          x: { grid: { display: false } }
        }
      }
    });
  }

  function renderYearlyBarChart(yearlyData) {
    if (!window.Chart || !yearlyData) return;
    destroyChart("yearlyBar");

    const ctx = document.getElementById("chart-yearly-bar");
    if (!ctx) return;

    const labels = yearlyData.map((y) => y.year);
    const totals = yearlyData.map((y) => y.total_mm);

    state.charts.yearlyBar = new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Annual Total Precipitation (mm)",
            data: totals,
            backgroundColor: "rgba(37, 99, 235, 0.85)",
            borderColor: "#2563EB",
            borderRadius: 6
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => `Year Total: ${ctx.raw.toLocaleString()} mm`
            }
          }
        },
        scales: {
          y: {
            title: { display: true, text: "Annual Rainfall (mm)" },
            grid: { color: "rgba(0, 0, 0, 0.05)" }
          },
          x: { grid: { display: false } }
        }
      }
    });
  }

  // ===================================================================
  // Rainfall Prediction Studio
  // ===================================================================

  function initPredictionStudio() {
    // Model Selection Cards (4 Architectures)
    const cardRF = document.getElementById("card-model-rf");
    const cardGB = document.getElementById("card-model-gb");
    const cardHurdle = document.getElementById("card-model-hurdle");
    const cardReg = document.getElementById("card-model-reg");
    const hiddenModelInput = document.getElementById("selected-model-input");

    const modelCards = [
      { el: cardRF, key: "ensemble" },
      { el: cardGB, key: "gradient_boosting" },
      { el: cardHurdle, key: "hurdle" },
      { el: cardReg, key: "regression" }
    ];

    modelCards.forEach((item) => {
      if (item.el) {
        item.el.addEventListener("click", () => {
          state.selectedModel = item.key;
          modelCards.forEach((c) => {
            if (c.el) c.el.classList.remove("selected");
          });
          item.el.classList.add("selected");
          if (hiddenModelInput) hiddenModelInput.value = item.key;
          showToast(`Switched model to: ${item.key.replace("_", " ").toUpperCase()}`, "info");

          // Auto-recalculate if live mode or result card is already open
          const resCard = document.getElementById("prediction-result-card");
          if (resCard && resCard.classList.contains("visible")) {
            handlePredictionSubmit();
          }
        });
      }
    });

    // Bidirectional Slider <-> Input Sync & Live Mode
    let liveDebounce = null;
    const pairs = [
      { input: "input-temp", range: "range-temp" },
      { input: "input-humidity", range: "range-humidity" },
      { input: "input-pressure", range: "range-pressure" },
      { input: "input-wind", range: "range-wind" },
      { input: "input-prev-rain", range: "range-prev-rain" }
    ];

    pairs.forEach(({ input, range }) => {
      const inEl = document.getElementById(input);
      const rgEl = document.getElementById(range);
      if (inEl && rgEl) {
        rgEl.addEventListener("input", (e) => {
          inEl.value = e.target.value;
          triggerLiveCalc();
        });
        inEl.addEventListener("input", (e) => {
          rgEl.value = e.target.value;
          triggerLiveCalc();
        });
      }
    });

    function triggerLiveCalc() {
      const toggle = document.getElementById("toggle-realtime-calc");
      if (toggle && toggle.checked) {
        clearTimeout(liveDebounce);
        liveDebounce = setTimeout(() => {
          handlePredictionSubmit();
        }, 180);
      }
    }

    // Presets
    document.querySelectorAll(".preset-chip[data-preset]").forEach((chip) => {
      chip.addEventListener("click", () => {
        const pKey = chip.dataset.preset;
        const p = PRESETS[pKey];
        if (!p) return;

        setVal("input-temp", p.temperature);
        setVal("range-temp", p.temperature);

        setVal("input-humidity", p.humidity);
        setVal("range-humidity", p.humidity);

        setVal("input-pressure", p.pressure);
        setVal("range-pressure", p.pressure);

        setVal("input-wind", p.wind_speed);
        setVal("range-wind", p.wind_speed);

        setVal("input-prev-rain", p.previous_rainfall);
        setVal("range-prev-rain", p.previous_rainfall);

        // Clear errors
        clearFormErrors();
        showToast(`Preset '${chip.innerText}' applied!`, "info");
        triggerLiveCalc();
      });
    });

    // Live Weather Auto-Fill Sync
    const btnFetchWeather = document.getElementById("btn-fetch-live-weather");
    const selectCity = document.getElementById("select-live-city");
    const statusWeather = document.getElementById("live-weather-status");

    async function syncWeather(cityKey, lat = null, lon = null) {
      if (statusWeather) {
        statusWeather.innerText = "⏳ Syncing atmosphere...";
        statusWeather.style.color = "var(--color-accent)";
      }
      try {
        let endpoint = `/api/weather/live?city=${cityKey}`;
        if (lat !== null && lon !== null) {
          endpoint = `/api/weather/live?lat=${lat}&lon=${lon}&city=custom&name=My%20Location`;
        }

        const res = await fetch(endpoint);
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Failed to fetch weather");

        setVal("input-temp", data.temperature);
        setVal("range-temp", data.temperature);

        setVal("input-humidity", data.humidity);
        setVal("range-humidity", data.humidity);

        setVal("input-pressure", data.pressure);
        setVal("range-pressure", data.pressure);

        setVal("input-wind", data.wind_speed);
        setVal("range-wind", data.wind_speed);

        setVal("input-prev-rain", data.previous_rainfall);
        setVal("range-prev-rain", data.previous_rainfall);

        clearFormErrors();
        if (statusWeather) {
          statusWeather.innerText = `✅ Synced: ${data.city} (${data.temperature}°C, ${data.humidity}% RH)`;
          statusWeather.style.color = "var(--color-success)";
        }
        showToast(`Synced real weather for ${data.city}`, "success");
        triggerLiveCalc();
      } catch (err) {
        console.error("Weather sync failed:", err);
        if (statusWeather) {
          statusWeather.innerText = "❌ Sync failed";
          statusWeather.style.color = "var(--color-red)";
        }
        showToast("Could not fetch live weather. Check internet connection.", "error");
      }
    }

    if (btnFetchWeather && selectCity) {
      btnFetchWeather.addEventListener("click", () => {
        syncWeather(selectCity.value);
      });
      selectCity.addEventListener("change", () => {
        syncWeather(selectCity.value);
      });
    }

    // Geolocation Support ("My GPS Location" button)
    const btnGeo = document.getElementById("btn-use-geolocation");
    if (btnGeo) {
      btnGeo.addEventListener("click", () => {
        if (!navigator.geolocation) {
          showToast("Geolocation is not supported by your browser.", "warning");
          return;
        }
        if (statusWeather) {
          statusWeather.innerText = "📍 Requesting GPS coordinates...";
          statusWeather.style.color = "var(--color-accent)";
        }
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            const lat = pos.coords.latitude.toFixed(4);
            const lon = pos.coords.longitude.toFixed(4);
            syncWeather("custom", lat, lon);
          },
          (err) => {
            console.warn("Geolocation denied/unavailable:", err);
            showToast("GPS access unavailable. Using selected city preset.", "warning");
            if (selectCity) syncWeather(selectCity.value);
          },
          { timeout: 7000 }
        );
      });
    }

    // Reset Form Button
    const btnReset = document.getElementById("btn-reset-form");
    if (btnReset) {
      btnReset.addEventListener("click", () => {
        setVal("input-temp", 28.0);
        setVal("range-temp", 28.0);
        setVal("input-humidity", 85.0);
        setVal("range-humidity", 85.0);
        setVal("input-pressure", 1004.0);
        setVal("range-pressure", 1004.0);
        setVal("input-wind", 16.5);
        setVal("range-wind", 16.5);
        setVal("input-prev-rain", 12.0);
        setVal("range-prev-rain", 12.0);
        clearFormErrors();
        const resCard = document.getElementById("prediction-result-card");
        if (resCard) resCard.classList.remove("visible");
      });
    }

    // Prediction Form Submission
    const predForm = document.getElementById("prediction-form");
    if (predForm) {
      predForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        await handlePredictionSubmit();
      });
    }
  }

  function validateInputs(formData) {
    let isValid = true;
    clearFormErrors();

    for (const [key, b] of Object.entries(BOUNDS)) {
      const val = parseFloat(formData[key]);
      if (isNaN(val) || val < b.min || val > b.max) {
        const errEl = document.getElementById(`error-${key === "wind_speed" ? "wind" : key === "previous_rainfall" ? "prev-rain" : key}`);
        const inputEl = document.getElementById(`input-${key === "wind_speed" ? "wind" : key === "previous_rainfall" ? "prev-rain" : key}`);
        if (errEl) errEl.classList.add("visible");
        if (inputEl) inputEl.classList.add("invalid");
        isValid = false;
      }
    }
    return isValid;
  }

  function clearFormErrors() {
    document.querySelectorAll(".form-error").forEach((el) => el.classList.remove("visible"));
    document.querySelectorAll(".form-input").forEach((el) => el.classList.remove("invalid"));
  }

  async function handlePredictionSubmit() {
    const payload = {
      model: state.selectedModel,
      temperature: parseFloat(getVal("input-temp")),
      humidity: parseFloat(getVal("input-humidity")),
      pressure: parseFloat(getVal("input-pressure")),
      wind_speed: parseFloat(getVal("input-wind")),
      previous_rainfall: parseFloat(getVal("input-prev-rain"))
    };

    if (!validateInputs(payload)) {
      showToast("Please correct the invalid input fields before submitting.", "error");
      return;
    }

    const btnSubmit = document.getElementById("btn-submit-predict");
    const loadingMsg = document.getElementById("predict-loading");
    if (btnSubmit) btnSubmit.disabled = true;
    if (loadingMsg) loadingMsg.style.display = "inline";

    try {
      const res = await fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Inference failed");

      displayPredictionResult(data);
      showToast(`Prediction generated: ${data.predicted_rainfall_mm} mm (${data.category})`, "success");

      // Update Latest Prediction in dashboard KPI
      setText("kpi-latest-pred", `${data.predicted_rainfall_mm.toFixed(1)} mm`);
      setText("kpi-latest-model", `${data.model_name} (${data.category})`);
    } catch (err) {
      console.error("Prediction error:", err);
      showToast(err.message, "error");
    } finally {
      if (btnSubmit) btnSubmit.disabled = false;
      if (loadingMsg) loadingMsg.style.display = "none";
    }
  }

  function displayPredictionResult(result) {
    const card = document.getElementById("prediction-result-card");
    if (!card) return;

    card.classList.add("visible");

    // Populate values
    setText("res-model-name", `${result.model_name} • ${result.algorithm}`);
    setText("res-prediction-id", result.prediction_id || "PRED-DONE");
    setText("res-rainfall-val", result.predicted_rainfall_mm.toFixed(2));

    // Category Badge
    const badge = document.getElementById("res-category-badge");
    if (badge) {
      badge.innerText = result.category;
      badge.className = `category-badge badge-${getBadgeClass(result.category)}`;
    }

    // Gauge Marker Positioning
    // Scale: 0 to 60 mm corresponds to 0% to 100%
    const gaugeVal = Math.min(60, Math.max(0, result.predicted_rainfall_mm));
    const gaugePct = (gaugeVal / 60) * 100;
    const marker = document.getElementById("res-gauge-marker");
    if (marker) {
      marker.style.left = `${gaugePct}%`;
    }
    setText("res-gauge-text", `${result.predicted_rainfall_mm.toFixed(2)} mm`);

    // Advisory
    const advBox = document.getElementById("res-advisory-box");
    if (advBox && result.advisory) {
      advBox.innerHTML = `<strong>Advisory (${result.advisory.severity}):</strong> ${result.advisory.message}`;
    }

    // Summary inputs
    setText("res-sum-temp", result.inputs_summary.temperature);
    setText("res-sum-humidity", result.inputs_summary.humidity);
    setText("res-sum-pressure", result.inputs_summary.pressure);
    setText("res-sum-wind", result.inputs_summary.wind_speed);
    setText("res-sum-prev", result.inputs_summary.previous_rainfall);
    setText("res-sum-latency", result.inference_latency_ms || "1.2");

    // Probability & Dew Point metrics
    if (result.rain_probability_pct !== undefined && result.rain_probability_pct !== null) {
      setText("res-prob-val", `${result.rain_probability_pct}%`);
    }
    if (result.xai) {
      setText("res-dew-val", `${result.xai.dew_point_c}°C`);
      setText("res-cond-val", result.xai.condensation_potential);

      // Render XAI Attribution Bars
      const xaiContainer = document.getElementById("res-xai-bars");
      if (xaiContainer && result.xai.attributions) {
        let xaiHtml = "";
        result.xai.attributions.forEach((attr) => {
          xaiHtml += `
            <div style="background: var(--color-surface-muted); padding: 0.85rem 1rem; border-radius: var(--radius-md); border: 1px solid var(--color-border);">
              <div style="display: flex; justify-content: space-between; font-size: 0.82rem; font-weight: 700; color: var(--color-primary);">
                <span>${attr.feature}</span>
                <span style="color: var(--color-accent); font-weight: 800;">${attr.weight_pct}%</span>
              </div>
              <div style="height: 6px; background: #E2E8F0; border-radius: 999px; margin-top: 6px; overflow: hidden;">
                <div style="width: ${attr.weight_pct}%; height: 100%; background: linear-gradient(90deg, var(--color-accent), var(--color-cyan)); border-radius: 999px;"></div>
              </div>
              <div style="font-size: 0.72rem; color: var(--color-text-muted); margin-top: 4px;">${attr.impact}</div>
            </div>
          `;
        });
        xaiContainer.innerHTML = xaiHtml;
      }
    }

    // Domain Impact & Operational Advisories (Flood & Agriculture)
    if (result.domain_advisory) {
      const flood = result.domain_advisory.urban_flood;
      const agri = result.domain_advisory.agriculture;

      if (flood) {
        setText("res-flood-pill", flood.level);
        const floodPill = document.getElementById("res-flood-pill");
        if (floodPill) {
          const pillColor = (flood.level === "MINIMAL" || flood.level === "LOW") ? "pill-green" :
                            flood.level === "WATCH" ? "pill-yellow" :
                            flood.level === "WARNING" ? "pill-orange" : "pill-red";
          floodPill.className = `domain-pill ${pillColor}`;
        }
        setText("res-flood-load", `${flood.drainage_load_pct}%`);
        const floodBar = document.getElementById("res-flood-bar");
        if (floodBar) {
          floodBar.style.width = `${Math.min(100, flood.drainage_load_pct)}%`;
          const fillColor = flood.drainage_load_pct < 40 ? "fill-green" :
                            flood.drainage_load_pct < 75 ? "fill-yellow" :
                            flood.drainage_load_pct < 100 ? "fill-orange" : "fill-red";
          floodBar.className = `domain-meter-fill ${fillColor}`;
        }
        setText("res-underpass-risk", flood.underpass_risk);
        setText("res-traffic-impact", flood.traffic_impact);
        setText("res-flood-action", flood.action_summary);
      }

      if (agri) {
        const agriPill = document.getElementById("res-agri-pill");
        if (agriPill) {
          const isOptimal = agri.spray_status.includes("Optimal");
          const isCaution = agri.spray_status.includes("Caution");
          const isProhib = agri.spray_status.includes("PROHIBITION");
          agriPill.innerText = isOptimal ? "OPTIMAL SPRAY" : isCaution ? "CAUTION" : isProhib ? "PROHIBITED" : "NO SPRAY";
          const pillColor = isOptimal ? "pill-green" : isCaution ? "pill-yellow" : isProhib ? "pill-red" : "pill-orange";
          agriPill.className = `domain-pill ${pillColor}`;
        }
        setText("res-agri-irrigation", agri.irrigation_advice);
        setText("res-agri-irrigation-desc", agri.irrigation_detail);
        setText("res-agri-spray", agri.spray_status);
        setText("res-agri-spray-desc", agri.spray_detail);
        setText("res-agri-field", agri.field_work);
      }
    }

    // Scroll smoothly to result card
    card.scrollIntoView({ behavior: "smooth", block: "nearest" });

    // Load 7-Day Forward Forecast Outlook
    load7DayForecast(result.inputs_summary);
  }

  async function load7DayForecast(inputs) {
    const strip = document.getElementById("forecast-7day-strip");
    if (!strip) return;

    try {
      const res = await fetch("/api/predict/7day-forecast", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(inputs)
      });
      const data = await res.json();
      if (!res.ok || !data.forecast) return;

      let html = "";
      data.forecast.forEach((d) => {
        const riskColor = (d.flood_risk === "MINIMAL" || d.flood_risk === "LOW") ? "pill-green" :
                          d.flood_risk === "WATCH" ? "pill-yellow" :
                          d.flood_risk === "WARNING" ? "pill-orange" : "pill-red";
        html += `
          <div class="forecast-day-card">
            <div class="forecast-day-date">${d.date}</div>
            <div class="forecast-day-icon">${d.weather_icon}</div>
            <div class="forecast-day-rain">${d.predicted_rainfall_mm.toFixed(1)} <span style="font-size: 0.72rem;">mm</span></div>
            <div class="forecast-day-prob">🌧 ${d.rain_probability_pct}%</div>
            <div class="forecast-day-temp">${d.temperature}°C • ${d.humidity}% RH</div>
            <div style="margin-top: 6px;">
              <span class="domain-pill ${riskColor}" style="padding: 2px 8px; font-size: 0.65rem;">${d.flood_risk}</span>
            </div>
          </div>
        `;
      });
      strip.innerHTML = html;
    } catch (err) {
      console.warn("7-day forecast error:", err);
    }
  }

  function getBadgeClass(category) {
    const cat = (category || "").toLowerCase();
    if (cat.includes("dry")) return "dry";
    if (cat.includes("light")) return "light";
    if (cat.includes("moderate")) return "moderate";
    if (cat.includes("heavy")) return "heavy";
    if (cat.includes("torrential")) return "torrential";
    return "dry";
  }

  // ===================================================================
  // Model Comparison Section
  // ===================================================================

  async function runModelComparison() {
    const payload = {
      temperature: parseFloat(getVal("input-temp")) || 28.0,
      humidity: parseFloat(getVal("input-humidity")) || 85.0,
      pressure: parseFloat(getVal("input-pressure")) || 1004.0,
      wind_speed: parseFloat(getVal("input-wind")) || 16.5,
      previous_rainfall: parseFloat(getVal("input-prev-rain")) || 12.0
    };

    try {
      const res = await fetch("/api/predict/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Comparison failed");

      // Update Banner
      setText("comp-val-reg", `${data.regression_model.predicted_rainfall_mm.toFixed(2)} mm`);
      const ensembleResult = data.ensemble_model || data.random_forest_model;
      const regVal = data.regression_model.predicted_rainfall_mm;
      const ensembleVal = ensembleResult.predicted_rainfall_mm;
      const comparisonDiff = Math.abs(regVal - ensembleVal);
      setText("comp-val-rf", `${ensembleVal.toFixed(2)} mm`);
      setText("comp-val-diff", `${comparisonDiff.toFixed(2)} mm`);
      setText("comp-val-consensus", comparisonDiff <= 8 ? "Strong Consensus" : "Divergent Forecast");

      // Side cards
      setText("comp-num-reg", data.regression_model.predicted_rainfall_mm.toFixed(2));
      setText("comp-cat-reg", data.regression_model.category);

      setText("comp-num-rf", ensembleVal.toFixed(2));
      setText("comp-cat-rf", ensembleResult.category);

      // Render Comparison Bar Chart with all models
      const rfVal = data.random_forest_model.predicted_rainfall_mm;
      const gbVal = data.gradient_boosting_model ? data.gradient_boosting_model.predicted_rainfall_mm : rfVal;
      const hVal = data.hurdle_model ? data.hurdle_model.predicted_rainfall_mm : rfVal;
      renderCompareBarChart(ensembleVal, rfVal, gbVal, hVal, regVal);

      // Load Metrics for scatter/residuals
      await loadMetricsAnalysis();
    } catch (err) {
      console.error("Comparison error:", err);
      showToast("Unable to run model comparison.", "error");
    }
  }

  function renderCompareBarChart(ensembleVal, rfVal, gbVal, hVal, regVal) {
    if (!window.Chart) return;
    destroyChart("compareBar");

    const ctx = document.getElementById("chart-compare-bar");
    if (!ctx) return;

    state.charts.compareBar = new Chart(ctx, {
      type: "bar",
      data: {
        labels: ["RainVision Ensemble", "Random Forest", "Gradient Boosting", "Two-Stage Hurdle", "Linear Regression"],
        datasets: [
          {
            label: "Predicted Rainfall (mm)",
            data: [ensembleVal, rfVal, gbVal, hVal, regVal],
            backgroundColor: ["#0EA5E9", "#38BDF8", "#06B6D4", "#10B981", "#1E293B"],
            borderRadius: 8,
            borderWidth: 1.5,
            borderColor: ["#0284C7", "#0284C7", "#0891B2", "#059669", "#0B132B"]
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.label}: ${ctx.raw.toFixed(2)} mm`
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            title: { display: true, text: "Rainfall (mm)" },
            grid: { color: "rgba(0,0,0,0.05)" }
          },
          x: { grid: { display: false } }
        }
      }
    });
  }

  async function loadMetricsAnalysis() {
    try {
      const res = await fetch("/api/models/metrics");
      if (!res.ok) return;
      const data = await res.json();
      state.metricsData = data;

      // Render Scatter / Residuals
      if (data.sample_predictions && data.sample_predictions.length) {
        renderScatterChart(data.sample_predictions);
      }
    } catch (err) {
      console.error("Metrics load error:", err);
    }
  }

  function renderScatterChart(samples) {
    if (!window.Chart || !samples) return;
    destroyChart("scatterResiduals");

    const ctx = document.getElementById("chart-scatter-residuals");
    if (!ctx) return;

    const ensemblePoints = samples.map((s) => ({ x: s.actual_mm, y: s.ensemble_predicted_mm }));
    const regPoints = samples.map((s) => ({ x: s.actual_mm, y: s.reg_predicted_mm }));

    state.charts.scatterResiduals = new Chart(ctx, {
      type: "scatter",
      data: {
        datasets: [
          {
            label: "RainVision Ensemble",
            data: ensemblePoints,
            backgroundColor: "rgba(34, 211, 238, 0.7)",
            borderColor: "#0891B2",
            borderWidth: 1,
            pointRadius: 4
          },
          {
            label: "Linear Regression",
            data: regPoints,
            backgroundColor: "rgba(37, 99, 235, 0.5)",
            borderColor: "#2563EB",
            borderWidth: 1,
            pointRadius: 3
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "top" },
          tooltip: {
            callbacks: {
              label: (ctx) => `Actual: ${ctx.parsed.x} mm, Predicted: ${ctx.parsed.y} mm`
            }
          }
        },
        scales: {
          x: {
            title: { display: true, text: "Actual Test Rainfall (mm)" },
            grid: { color: "rgba(0,0,0,0.05)" }
          },
          y: {
            title: { display: true, text: "Predicted Rainfall (mm)" },
            grid: { color: "rgba(0,0,0,0.05)" }
          }
        }
      }
    });
  }

  // ===================================================================
  // Dataset Explorer Section
  // ===================================================================

  async function loadDatasetExplorer() {
    const q = new URLSearchParams({
      page: state.explorer.page,
      limit: state.explorer.limit,
      search: state.explorer.search,
      year: state.explorer.year,
      rain: state.explorer.rain,
      sort_by: state.explorer.sortBy,
      sort_order: state.explorer.sortOrder
    });

    try {
      const res = await fetch(`/api/dataset/preview?${q.toString()}`);
      if (!res.ok) throw new Error("Failed to load dataset records");
      const data = await res.json();

      state.explorer.totalPages = data.pagination.total_pages;

      renderExplorerTable(data.records, data.pagination);
    } catch (err) {
      console.error("Dataset load error:", err);
      showToast("Unable to fetch dataset records.", "error");
    }
  }

  function renderExplorerTable(records, pagination) {
    const tbody = document.getElementById("dataset-tbody");
    if (!tbody) return;

    if (!records || !records.length) {
      tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; padding: 2rem; color: var(--color-text-muted);">No records found matching your filters.</td></tr>`;
      return;
    }

    let rowsHtml = "";
    records.forEach((r) => {
      const badgeCls = getBadgeClass(r.category);
      const rowJson = JSON.stringify(r).replace(/'/g, "&#39;");
      rowsHtml += `
        <tr>
          <td><strong>${r.date}</strong></td>
          <td>${r.location}</td>
          <td><strong style="color: var(--color-primary);">${r.rainfall.toFixed(2)} mm</strong></td>
          <td><span class="category-badge badge-${badgeCls}" style="padding: 2px 8px; font-size: 0.75rem;">${r.category}</span></td>
          <td>${r.temperature.toFixed(1)} °C</td>
          <td>${r.humidity.toFixed(1)} %</td>
          <td>${r.pressure.toFixed(1)} hPa</td>
          <td>${r.wind_speed.toFixed(1)} km/h</td>
          <td>${r.previous_rainfall.toFixed(2)} mm</td>
          <td style="text-align: center;">
            <button type="button" class="btn-test-row" data-row='${rowJson}'>
              ⚡ Test ML
            </button>
          </td>
        </tr>
      `;
    });
    tbody.innerHTML = rowsHtml;

    // Attach Ground-Truth Test Handlers
    document.querySelectorAll(".btn-test-row").forEach((btn) => {
      btn.addEventListener("click", () => {
        try {
          const rowData = JSON.parse(btn.dataset.row);
          testHistoricalRow(rowData);
        } catch (e) {
          console.error("Row parse error:", e);
        }
      });
    });

    // Update Pagination UI
    const startIdx = (pagination.page - 1) * pagination.limit + 1;
    const endIdx = Math.min(pagination.page * pagination.limit, pagination.total_records);

    setText("pagination-start", startIdx);
    setText("pagination-end", endIdx);
    setText("pagination-total", pagination.total_records.toLocaleString());
    setText("pagination-current-page", `Page ${pagination.page} of ${pagination.total_pages}`);
    setText("table-record-count", `${pagination.total_records.toLocaleString()} records`);

    const prevBtn = document.getElementById("btn-page-prev");
    const nextBtn = document.getElementById("btn-page-next");
    if (prevBtn) prevBtn.disabled = pagination.page <= 1;
    if (nextBtn) nextBtn.disabled = pagination.page >= pagination.total_pages;
  }

  async function testHistoricalRow(row) {
    // 1. Populate all inputs and sliders
    setVal("input-temp", row.temperature);
    setVal("range-temp", row.temperature);
    setVal("input-humidity", row.humidity);
    setVal("range-humidity", row.humidity);
    setVal("input-pressure", row.pressure);
    setVal("range-pressure", row.pressure);
    setVal("input-wind", row.wind_speed);
    setVal("range-wind", row.wind_speed);
    setVal("input-prev-rain", row.previous_rainfall);
    setVal("range-prev-rain", row.previous_rainfall);

    clearFormErrors();

    // 2. Run prediction
    const payload = {
      model: state.selectedModel,
      temperature: row.temperature,
      humidity: row.humidity,
      pressure: row.pressure,
      wind_speed: row.wind_speed,
      previous_rainfall: row.previous_rainfall
    };

    try {
      const res = await fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);

      displayPredictionResult(data);

      // 3. Ground truth comparison display
      const gtBox = document.getElementById("ground-truth-box");
      if (gtBox) {
        gtBox.style.display = "block";
        setText("gt-date-label", `Observed Station Record: ${row.date} (${row.location})`);
        setText("gt-actual-rain", `${row.rainfall.toFixed(2)} mm`);
        setText("gt-predicted-rain", `${data.predicted_rainfall_mm.toFixed(2)} mm`);

        const diff = Math.abs(row.rainfall - data.predicted_rainfall_mm);
        setText("gt-diff-rain", `±${diff.toFixed(2)} mm`);

        const baseVal = Math.max(row.rainfall, 8.0);
        const accuracy = Math.max(0, Math.min(100, 100 - (diff / baseVal) * 100)).toFixed(1);
        const accBadge = document.getElementById("gt-accuracy-badge");
        if (accBadge) {
          accBadge.innerText = `${accuracy}% Skill Score`;
          accBadge.className = `domain-pill ${accuracy >= 80 ? 'pill-green' : accuracy >= 50 ? 'pill-yellow' : 'pill-orange'}`;
        }
      }

      showToast(`Tested historical record ${row.date}: Observed ${row.rainfall.toFixed(1)}mm vs Pred ${data.predicted_rainfall_mm.toFixed(1)}mm`, "success");

      // Scroll smoothly to prediction section
      const predSection = document.getElementById("section-prediction");
      if (predSection) predSection.scrollIntoView({ behavior: "smooth" });
    } catch (err) {
      showToast(`Ground-truth test failed: ${err.message}`, "error");
    }
  }

  function initDatasetExplorerListeners() {
    // Search input
    let searchTimeout = null;
    const searchInput = document.getElementById("table-search-input");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
          state.explorer.search = e.target.value.trim();
          state.explorer.page = 1;
          loadDatasetExplorer();
        }, 300);
      });
    }

    // Year filter (Populate dynamically from 2026 down to 1985)
    const yearSelect = document.getElementById("filter-year");
    if (yearSelect) {
      let opts = '<option value="all">All Years (1985–2026 / 42 Years)</option>';
      for (let y = 2026; y >= 1985; y--) {
        opts += `<option value="${y}">${y}</option>`;
      }
      yearSelect.innerHTML = opts;

      yearSelect.addEventListener("change", (e) => {
        state.explorer.year = e.target.value;
        state.explorer.page = 1;
        loadDatasetExplorer();
      });
    }

    // Rainfall filter
    const rainSelect = document.getElementById("filter-rainfall");
    if (rainSelect) {
      rainSelect.addEventListener("change", (e) => {
        state.explorer.rain = e.target.value;
        state.explorer.page = 1;
        loadDatasetExplorer();
      });
    }

    // Sorting
    document.querySelectorAll("#dataset-table th[data-sort]").forEach((th) => {
      th.addEventListener("click", () => {
        const field = th.dataset.sort;
        if (state.explorer.sortBy === field) {
          state.explorer.sortOrder = state.explorer.sortOrder === "asc" ? "desc" : "asc";
        } else {
          state.explorer.sortBy = field;
          state.explorer.sortOrder = "asc";
        }
        loadDatasetExplorer();
      });
    });

    // Pagination buttons
    const prevBtn = document.getElementById("btn-page-prev");
    if (prevBtn) {
      prevBtn.addEventListener("click", () => {
        if (state.explorer.page > 1) {
          state.explorer.page--;
          loadDatasetExplorer();
        }
      });
    }

    const nextBtn = document.getElementById("btn-page-next");
    if (nextBtn) {
      nextBtn.addEventListener("click", () => {
        if (state.explorer.page < state.explorer.totalPages) {
          state.explorer.page++;
          loadDatasetExplorer();
        }
      });
    }

    // 7-Day Trajectory Refresh Button
    const btnRefresh7Day = document.getElementById("btn-refresh-7day");
    if (btnRefresh7Day) {
      btnRefresh7Day.addEventListener("click", () => {
        const payload = {
          temperature: parseFloat(getVal("input-temp")),
          humidity: parseFloat(getVal("input-humidity")),
          pressure: parseFloat(getVal("input-pressure")),
          wind_speed: parseFloat(getVal("input-wind")),
          previous_rainfall: parseFloat(getVal("input-prev-rain"))
        };
        load7DayForecast(payload);
        showToast("7-Day forward weather trajectory recalculated!", "info");
      });
    }

    // CSV Batch Processing & Upload Form
    const uploadForm = document.getElementById("upload-form");
    if (uploadForm) {
      uploadForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fileInput = document.getElementById("upload-csv-file");
        const submitBtn = document.getElementById("btn-submit-upload");
        if (!fileInput || !fileInput.files.length) {
          showToast("Please choose a CSV file to upload.", "error");
          return;
        }

        const formData = new FormData();
        formData.append("file", fileInput.files[0]);

        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.innerText = "⏳ Processing Models...";
        }

        try {
          const res = await fetch("/api/dataset/upload", {
            method: "POST",
            body: formData
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.error || "Upload failed");

          const resBox = document.getElementById("upload-result-box");
          const resMsg = document.getElementById("upload-result-msg");
          const badgesEl = document.getElementById("upload-stats-badges");
          const btnDownloadBatch = document.getElementById("btn-download-batch-csv");
          const previewWrap = document.getElementById("batch-preview-wrapper");
          const previewTbody = document.getElementById("batch-preview-tbody");

          if (resBox && resMsg) {
            resBox.style.display = "block";
            resMsg.innerHTML = `
              <strong>Dataset:</strong> ${data.filename} (${data.rows.toLocaleString()} daily observations parsed)<br>
              <strong>Schema Validation:</strong> <code>${data.columns.join(", ")}</code><br>
              <strong>Data Quality:</strong> ${data.missing_values} missing values handled, ${data.duplicate_rows} duplicates detected.
            `;
          }

          if (data.batch_summary && badgesEl) {
            badgesEl.innerHTML = `
              <span class="domain-pill pill-green">Batch Processed: ${data.batch_summary.total_rows} rows</span>
              <span class="domain-pill pill-yellow">Wet Days: ${data.batch_summary.predicted_rainy_days}</span>
              <span class="domain-pill pill-orange">Max Rain: ${data.batch_summary.max_predicted_rainfall_mm} mm</span>
              <span class="domain-pill pill-red">Torrential Events: ${data.batch_summary.torrential_events_count}</span>
            `;
          }

          if (btnDownloadBatch) {
            btnDownloadBatch.style.display = "inline-flex";
          }

          if (data.preview_records && previewWrap && previewTbody) {
            previewWrap.style.display = "block";
            let previewHtml = "";
            data.preview_records.forEach((pr) => {
              const pillColor = (pr.flood_alert === "MINIMAL" || pr.flood_alert === "LOW") ? "pill-green" :
                                pr.flood_alert === "WATCH" ? "pill-yellow" : "pill-orange";
              previewHtml += `
                <tr>
                  <td>${pr.temperature}°C</td>
                  <td>${pr.humidity}%</td>
                  <td>${pr.pressure} hPa</td>
                  <td><strong style="color: var(--color-primary);">${pr.predicted_rf} mm</strong></td>
                  <td>${pr.rain_prob}%</td>
                  <td><span class="category-badge badge-${getBadgeClass(pr.category)}" style="padding: 2px 6px; font-size: 0.72rem;">${pr.category}</span></td>
                  <td><span class="domain-pill ${pillColor}" style="padding: 2px 6px; font-size: 0.65rem;">${pr.flood_alert}</span></td>
                </tr>
              `;
            });
            previewTbody.innerHTML = previewHtml;
          }

          showToast(`Batch ML inference completed on ${data.filename}!`, "success");
        } catch (err) {
          showToast(err.message, "error");
        } finally {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerText = "⚡ Process Batch Predictions";
          }
        }
      });
    }
  }

  // ===================================================================
  // Historical Analytics Section
  // ===================================================================

  async function loadAnalytics() {
    try {
      const res = await fetch("/api/rainfall/trends");
      if (!res.ok) throw new Error("Failed to load historical analytics");
      const data = await res.json();

      if (!window.Chart) return;
      destroyChart("analyticsYearly");

      const ctx = document.getElementById("chart-analytics-yearly");
      if (!ctx) return;

      state.charts.analyticsYearly = new Chart(ctx, {
        type: "line",
        data: {
          labels: data.years,
          datasets: [
            {
              label: "Total Annual Rainfall (mm)",
              data: data.yearly_totals,
              borderColor: "#2563EB",
              backgroundColor: "rgba(37, 99, 235, 0.15)",
              borderWidth: 3,
              fill: true,
              tension: 0.3,
              pointRadius: 6,
              pointBackgroundColor: "#22D3EE"
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: "top" },
            tooltip: {
              callbacks: {
                label: (ctx) => `Annual Precipitation: ${ctx.raw.toLocaleString()} mm`
              }
            }
          },
          scales: {
            y: {
              title: { display: true, text: "Annual Total (mm)" },
              grid: { color: "rgba(0,0,0,0.05)" }
            },
            x: { grid: { display: false } }
          }
        }
      });
    } catch (err) {
      console.error("Analytics load error:", err);
    }
  }

  // ===================================================================
  // Utility Helpers
  // ===================================================================

  function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.innerText = text;
  }

  function getVal(id) {
    const el = document.getElementById(id);
    return el ? el.value : "";
  }

  function setVal(id, val) {
    const el = document.getElementById(id);
    if (el) el.value = val;
  }

  // ===================================================================
  // Application Bootstrap
  // ===================================================================

  document.addEventListener("DOMContentLoaded", () => {
    initNavigation();
    initPredictionStudio();
    initDatasetExplorerListeners();

    // Refresh Dashboard button
    const btnRefDash = document.getElementById("btn-refresh-dashboard");
    if (btnRefDash) {
      btnRefDash.addEventListener("click", () => {
        loadDashboard();
        showToast("Dashboard analytics refreshed.", "info");
      });
    }

    // Comparison Trigger Button on Compare Page
    const btnRunComp = document.getElementById("btn-run-comparison");
    if (btnRunComp) {
      btnRunComp.addEventListener("click", () => {
        runModelComparison();
        showToast("Model comparison re-calculated.", "info");
      });
    }

    // Auto-load dashboard on init
    loadDashboard();
  });
})();
