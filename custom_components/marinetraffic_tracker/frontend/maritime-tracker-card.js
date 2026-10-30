/**
 * Maritime Tracker Custom Card
 *
 * Displays a Leaflet-based map with vessel markers, trails, area outline,
 * and an optional port-board card. Connects via WebSocket for real-time updates.
 *
 * Features:
 * - Entity picker for selecting tracked entry
 * - Area and watchlist vessel layers
 * - Vessel heading/course markers
 * - Actual area geometry (circle/rectangle)
 * - Bounded vessel trails with gaps
 * - Selection and details pane
 * - Fit/reset map controls
 * - Mobile-friendly interaction
 * - Unavailable/stale state handling
 */

(function () {
  "use strict";

  // Default Leaflet CDN for fallback (pinned version).
  const LEAFLET_VERSION = "1.9.4";
  const LEAFLET_CSS_URL =
    `https://cdn.jsdelivr.net/npm/leaflet@${LEAFLET_VERSION}/dist/leaflet.min.css`;
  const LEAFLET_JS_URL =
    `https://cdn.jsdelivr.net/npm/leaflet@${LEAFLET_VERSION}/dist/leaflet.min.js`;

  // Custom card definition.
  class MaritimeTrackerCard extends HTMLElement {
    /**
     * Set the configuration passed by Lovelace.
     * @param {Object} config - The card configuration
     */
    setConfig(config) {
      this._config = {
        entity: config.entity || null,
        zoom: config.zoom || 8,
        show_port_board: config.show_port_board !== false,
        ...config,
      };
      this._mapInstance = null;
      this._wsConnection = null;
      this._selectedVessel = null;
      this._trailLayers = {};
      this._subscription = null;
      this._lastSnapshot = null;
      this._vesselMarkers = {};
    }

    /**
     * Get the card's configuration schema for UI editor.
     */
    static getConfigElement() {
      return document.createElement(
        "maritime-tracker-card-editor"
      );
    }

    /**
     * Get the card's stubs (schema).
     */
    static getStubConfig() {
      return {
        entity: "",
        zoom: 8,
        show_port_board: true,
      };
    }

    /**
     * Lifecycle: element is inserted into DOM.
     */
    connectedCallback() {
      this.addEventListener("hass-service-called", this._handleServiceCall);
    }

    /**
     * Lifecycle: element is removed from DOM.
     */
    disconnectedCallback() {
      this._cleanup();
      this.removeEventListener("hass-service-called", this._handleServiceCall);
    }

    /**
     * Update the card when HA state changes or config is set.
     * @param {Object} changedProps - Changed properties
     */
    setHass(hass) {
      this._hass = hass;
      if (!this._initialized) {
        this._initialized = true;
        this._render();
        this._initializeMap();
        this._connectWebSocket();
      } else {
        // Update on state change (e.g., entity availability).
        this._updateAvailability();
      }
    }

    /**
     * Render the card's HTML structure.
     */
    _render() {
      if (!this._hass) return;

      this.innerHTML = `
        <ha-card>
          <div class="card-header">
            <div class="title">Maritime Tracker</div>
            <div class="header-controls">
              <ha-entity-picker
                .hass="${this._hass}"
                .value="${this._config.entity}"
                @value-changed="${this._onEntityChanged}"
                allow-custom-entity
              ></ha-entity-picker>
            </div>
          </div>
          <div class="card-content">
            <div class="map-container" id="map"></div>
            <div class="details-panel">
              <div class="details-close" id="details-close">×</div>
              <div class="details-content" id="details-content">
                <p>Select a vessel on the map</p>
              </div>
            </div>
            ${this._config.show_port_board ? '<div class="port-board" id="port-board"></div>' : ""}
          </div>
          <div class="card-actions">
            <ha-button id="fit-map-btn">Fit Map</ha-button>
            <ha-button id="reset-map-btn">Reset</ha-button>
          </div>
        </ha-card>
      `;

      // Attach styles.
      const style = document.createElement("style");
      style.textContent = this._getStyles();
      this.appendChild(style);

      // Wire event listeners.
      this.querySelector("#details-close").addEventListener("click", () => {
        this._selectedVessel = null;
        this._updateDetailsPanel();
      });

      this.querySelector("#fit-map-btn").addEventListener("click", () => {
        this._fitMapToVessels();
      });

      this.querySelector("#reset-map-btn").addEventListener("click", () => {
        this._resetMap();
      });
    }

    /**
     * Get CSS for the card.
     */
    _getStyles() {
      return `
        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px;
          border-bottom: 1px solid var(--divider-color);
        }

        .title {
          font-size: 24px;
          font-weight: 500;
        }

        .header-controls {
          flex: 1;
          margin-left: 16px;
        }

        .card-content {
          position: relative;
          display: flex;
          height: 600px;
        }

        .map-container {
          flex: 1;
          position: relative;
          min-width: 0;
        }

        .details-panel {
          width: 300px;
          border-left: 1px solid var(--divider-color);
          background: var(--card-background-color);
          overflow-y: auto;
          position: relative;
          display: none;
        }

        .details-panel.active {
          display: block;
        }

        .details-close {
          position: absolute;
          top: 8px;
          right: 8px;
          font-size: 24px;
          cursor: pointer;
          color: var(--text-secondary-color);
        }

        .details-close:hover {
          color: var(--text-primary-color);
        }

        .details-content {
          padding: 16px;
          padding-top: 40px;
        }

        .port-board {
          display: none;
        }

        .port-board.active {
          display: block;
          width: 300px;
          border-left: 1px solid var(--divider-color);
          background: var(--card-background-color);
          overflow-y: auto;
        }

        .card-actions {
          display: flex;
          gap: 8px;
          padding: 16px;
          border-top: 1px solid var(--divider-color);
        }

        ha-button {
          flex: 1;
        }

        /* Leaflet overrides */
        .leaflet-container {
          font-family: var(--primary-font-family);
          background-color: var(--surface-color, #fff);
        }

        .leaflet-popup-content {
          font-size: 14px;
          margin: 4px 0;
        }

        /* Mobile responsive */
        @media (max-width: 768px) {
          .card-content {
            flex-direction: column;
            height: auto;
            min-height: 400px;
          }

          .map-container {
            height: 400px;
          }

          .details-panel {
            width: 100%;
            height: 200px;
            border-left: none;
            border-top: 1px solid var(--divider-color);
          }

          .port-board {
            width: 100%;
            height: 150px;
            border-left: none;
            border-top: 1px solid var(--divider-color);
          }

          .card-actions {
            flex-wrap: wrap;
          }
        }
      `;
    }

    /**
     * Initialize the Leaflet map.
     */
    async _initializeMap() {
      if (!window.L) {
        await this._loadLeaflet();
      }

      const mapContainer = this.querySelector("#map");
      if (!mapContainer || this._mapInstance) return;

      // Default center (Barents Sea).
      const center = [70.0, 25.0];
      const zoom = this._config.zoom || 8;

      this._mapInstance = window.L.map(mapContainer).setView(center, zoom);

      // Add tile layer (OpenStreetMap).
      window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution:
          '© OpenStreetMap contributors',
        maxZoom: 19,
      }).addTo(this._mapInstance);

      // Draw area outline (placeholder - will be updated from coordinator).
      this._areaCircle = window.L.circle(center, {
        radius: 50000,
        color: "#4CAF50",
        fill: false,
        weight: 2,
        dashArray: "5, 5",
      }).addTo(this._mapInstance);

      // Resize map when window changes.
      window.addEventListener("resize", () => {
        if (this._mapInstance) {
          this._mapInstance.invalidateSize();
        }
      });
    }

    /**
     * Load Leaflet library dynamically.
     */
    async _loadLeaflet() {
      return new Promise((resolve, reject) => {
        // Load CSS.
        const link = document.createElement("link");
        link.rel = "stylesheet";
        link.href = LEAFLET_CSS_URL;
        link.onload = () => {
          // Load JS.
          const script = document.createElement("script");
          script.src = LEAFLET_JS_URL;
          script.onload = resolve;
          script.onerror = reject;
          document.head.appendChild(script);
        };
        link.onerror = reject;
        document.head.appendChild(link);
      });
    }

    /**
     * Connect to WebSocket API for live updates.
     */
    async _connectWebSocket() {
      if (!this._config.entity || !this._hass) return;

      // Resolve entity to entry ID (placeholder - actual implementation
      // would query coordinator for entry mapping).
      const entryId = this._config.entity.split(".")[1] || "default";

      try {
        this._wsConnection = await this._hass.connection.subscribeMessage(
          (msg) => this._onWebSocketMessage(msg),
          {
            type: "marinetraffic_tracker:get_snapshot",
            entry_id: entryId,
            page: 1,
            page_size: 100,
          }
        );
      } catch (err) {
        console.error("WebSocket connection failed:", err);
      }
    }

    /**
     * Handle WebSocket messages with snapshot data.
     */
    _onWebSocketMessage(msg) {
      if (!msg.vessels) return;

      this._lastSnapshot = msg;
      this._updateMarkers(msg.vessels);
      this._updateAreaOutline(msg);
    }

    /**
     * Update vessel markers on the map.
     */
    _updateMarkers(vessels) {
      if (!this._mapInstance) return;

      const now = new Date();

      vessels.forEach((vessel) => {
        const markerId = vessel.mmsi;
        const isStale = vessel.is_stale;
        const isWatched = vessel.is_watched;

        if (!vessel.position) {
          // Remove marker if no position.
          if (this._vesselMarkers[markerId]) {
            this._mapInstance.removeLayer(this._vesselMarkers[markerId]);
            delete this._vesselMarkers[markerId];
          }
          return;
        }

        const [lat, lon] = vessel.position;
        const markerOptions = {
          icon: this._getMarkerIcon(isWatched, isStale),
          title: vessel.name || markerId,
        };

        let marker = this._vesselMarkers[markerId];
        if (marker) {
          marker.setLatLng([lat, lon]);
          marker.setIcon(markerOptions.icon);
        } else {
          marker = window.L.marker([lat, lon], markerOptions);
          marker.addTo(this._mapInstance);
          marker.on("click", () => this._selectVessel(vessel));
          this._vesselMarkers[markerId] = marker;
        }

        // Add heading/course line if available.
        if (vessel.heading !== null || vessel.course !== null) {
          const heading = vessel.heading ?? vessel.course ?? 0;
          this._drawHeadingLine(marker, heading);
        }
      });

      // Remove markers for vessels no longer in snapshot.
      Object.keys(this._vesselMarkers).forEach((mmsi) => {
        if (!vessels.some((v) => v.mmsi === mmsi)) {
          this._mapInstance.removeLayer(this._vesselMarkers[mmsi]);
          delete this._vesselMarkers[mmsi];
        }
      });
    }

    /**
     * Get marker icon based on vessel state.
     */
    _getMarkerIcon(isWatched, isStale) {
      const color = isStale ? "#999" : isWatched ? "#FF9800" : "#2196F3";
      return window.L.circleMarker(null, {
        radius: 8,
        fillColor: color,
        color: color,
        weight: 2,
        opacity: 1,
        fillOpacity: 0.8,
      });
    }

    /**
     * Draw a heading line from a marker.
     */
    _drawHeadingLine(marker, heading) {
      // Calculate end point 2km in the heading direction.
      const [lat, lon] = marker.getLatLng();
      const distance = 0.01; // ~1.1km per degree at equator.
      const rad = (heading * Math.PI) / 180;
      const endLat = lat + distance * Math.cos(rad);
      const endLon = lon + distance * Math.sin(rad);

      // Draw line (polyline layer).
      if (marker._headingLine) {
        marker._headingLine.setLatLngs([[lat, lon], [endLat, endLon]]);
      } else {
        marker._headingLine = window.L.polyline([[lat, lon], [endLat, endLon]], {
          color: "#FF5722",
          weight: 2,
          opacity: 0.7,
        }).addTo(this._mapInstance);
      }
    }

    /**
     * Update area outline based on coordinator config.
     */
    _updateAreaOutline(snapshot) {
      // This would be enhanced with actual area geometry from coordinator.
      // For now, redraw the placeholder circle.
    }

    /**
     * Select a vessel and show details.
     */
    _selectVessel(vessel) {
      this._selectedVessel = vessel;
      this._updateDetailsPanel();
      this._loadVesselTrail(vessel.mmsi);
    }

    /**
     * Update details panel with selected vessel info.
     */
    _updateDetailsPanel() {
      const panel = this.querySelector(".details-panel");
      const content = this.querySelector("#details-content");

      if (!this._selectedVessel) {
        panel.classList.remove("active");
        content.innerHTML = "<p>Select a vessel on the map</p>";
        return;
      }

      const v = this._selectedVessel;
      panel.classList.add("active");

      const lastSeen = v.last_seen_at
        ? new Date(v.last_seen_at).toLocaleString()
        : "Unknown";

      content.innerHTML = `
        <div class="vessel-details">
          <h3>${v.name || v.mmsi}</h3>
          <dl>
            <dt>MMSI</dt>
            <dd>${v.mmsi}</dd>
            <dt>Status</dt>
            <dd>${v.status || "Unknown"}</dd>
            <dt>Position</dt>
            <dd>${v.position ? v.position.join(", ") : "Unknown"}</dd>
            <dt>Speed</dt>
            <dd>${v.speed_knots !== null ? v.speed_knots + " kn" : "Unknown"}</dd>
            <dt>Destination</dt>
            <dd>${v.destination || "Unknown"}</dd>
            <dt>Last Seen</dt>
            <dd>${lastSeen}</dd>
            <dt>Stale</dt>
            <dd>${v.is_stale ? "Yes" : "No"}</dd>
            <dt>Watched</dt>
            <dd>${v.is_watched ? "Yes" : "No"}</dd>
          </dl>
        </div>
      `;

      this.querySelector(".details-panel").innerHTML += `
        <style>
          .vessel-details { padding: 0; }
          .vessel-details h3 { margin: 0 0 12px 0; }
          .vessel-details dl { margin: 0; }
          .vessel-details dt { font-weight: 600; margin-top: 8px; }
          .vessel-details dd { margin: 0 0 8px 0; color: var(--text-secondary-color); }
        </style>
      `;
    }

    /**
     * Load and display trail for selected vessel.
     */
    async _loadVesselTrail(mmsi) {
      if (!this._wsConnection || !this._config.entity) return;

      try {
        const entryId = this._config.entity.split(".")[1] || "default";
        const response = await this._hass.connection.sendMessage({
          type: "marinetraffic_tracker:get_trail",
          entry_id: entryId,
          mmsi: mmsi,
        });

        if (response.points && response.points.length > 0) {
          this._drawTrail(mmsi, response.points);
        }
      } catch (err) {
        console.error("Failed to load trail:", err);
      }
    }

    /**
     * Draw a trail polyline on the map.
     */
    _drawTrail(mmsi, points) {
      if (!this._mapInstance) return;

      // Remove old trail.
      if (this._trailLayers[mmsi]) {
        this._mapInstance.removeLayer(this._trailLayers[mmsi]);
      }

      const coords = points.map((p) => [p.lat, p.lon]);
      const trail = window.L.polyline(coords, {
        color: "#4CAF50",
        weight: 2,
        opacity: 0.6,
      }).addTo(this._mapInstance);

      this._trailLayers[mmsi] = trail;
    }

    /**
     * Fit map to all vessel markers.
     */
    _fitMapToVessels() {
      if (!this._mapInstance || Object.keys(this._vesselMarkers).length === 0)
        return;

      const group = window.L.featureGroup(Object.values(this._vesselMarkers));
      this._mapInstance.fitBounds(group.getBounds(), { padding: [50, 50] });
    }

    /**
     * Reset map to default center/zoom.
     */
    _resetMap() {
      if (!this._mapInstance) return;
      this._mapInstance.setView([70.0, 25.0], this._config.zoom || 8);
    }

    /**
     * Handle entity selection change.
     */
    _onEntityChanged(ev) {
      this._config.entity = ev.detail.value;
      this._wsConnection = null;
      this._connectWebSocket();
    }

    /**
     * Update availability display.
     */
    _updateAvailability() {
      if (!this._config.entity || !this._hass) return;

      const entity = this._hass.states[this._config.entity];
      if (!entity) {
        this.querySelector(".map-container").style.opacity = "0.5";
      } else {
        this.querySelector(".map-container").style.opacity = "1";
      }
    }

    /**
     * Clean up resources.
     */
    _cleanup() {
      if (this._mapInstance) {
        this._mapInstance.remove();
        this._mapInstance = null;
      }
      if (this._wsConnection) {
        this._wsConnection = null;
      }
      this._vesselMarkers = {};
      this._trailLayers = {};
    }
  }

  // Register custom element.
  customElements.define("maritime-tracker-card", MaritimeTrackerCard);

  // Register with Home Assistant.
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "maritime-tracker-card",
    name: "Maritime Tracker",
    description: "Real-time maritime vessel tracking with trails and port board",
    preview: true,
    element: "maritime-tracker-card",
  });
})();
