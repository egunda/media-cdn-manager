# VERSION INFO

## v0.1.0 (2026-01-10)

### Major UI/UX Refactor
- **Floating Deployment Monitor**: Moved static progress sidebar to a floating window in the bottom-right corner.
- **Persistent Bottom Bar**: Added a minimized "GCP Deployment" progress bar at the bottom for background monitoring.
- **Dynamic Controls**: Implemented Minimize, Expand, and Close logic for the deployment window.
- **Full-Width Setup**: Expanded the configuration form to take the full width of the portal, improving usability.
- **Max-Width Convergence**: Fixed layout issues where sections were spreading beyond the 7xl container.

### Backend & Integration Enhancements
- **GCS Resource Discovery**: Added `/api/buckets` endpoint to dynamically list GCS buckets for origin creation.
- **Advanced Origin Support**: Enhanced the Origin Creation Modal and Backend to support:
  - Custom Descriptions
  - Protocol selection (HTTP, HTTPS, HTTP2)
  - Custom Port configuration
  - Request Host Header overrides (commonOverride.hostHeader)
- **Infrastructure Poll Sync**: Fixed redundant polling loops and synchronized plural endpoint naming (`/api/origins`).
- **Native Implementation**: Fully established an airlock-compatible backend using Python's standard libraries (`urllib`, `http.server`, `openssl`).

## v0.1.1 (2026-01-10)

### UI/UX Responsiveness
- **Immediate Deployment Feedback**: Fixed 20-second delay in progress monitoring by implementing immediate polling upon button click.
- **Enhanced Polling Frequency**: Reduced polling interval from 20s to 10s for more real-time progress updates.
- **State Persistence**: Ensured the progress window is automatically shown when a deployment is active, even if the user closed it accidentally.
- **Improved UI Resets**: Implemented clean resets for progress bars and labels when starting new deployment tasks.

## v0.1.4 (2026-01-10)

### Dual Token Security (HLS)
- **HMAC-SHA256 Protection**: Implemented dual-token authentication specifically for HLS streaming (Master Manifest, Child Manifest, and TS Segments).
- **Secret Manager Integration**: Automated creation of HMAC secrets and secure handling via Google Cloud Secret Manager.
- **Automated IAM Provisioning**: Dynamically grants `secretmanager.secretAccessor` permissions to the Media CDN service account.
- **Keyset Management**: Supports selecting existing Keysets or dynamically creating new ones (Short and Google-Managed Long keysets).
- **Security-First Templates**: Built-in logic to apply `GENERATE_TOKEN_HLS_COOKIELESS` and `PROPAGATE_TOKEN_HLS_COOKIELESS` actions to HLS paths.

## v0.1.5 (2026-01-12)

### Premium Dark Mode
- **Full Theme Toggle**: Integrated a theme selector in the header for switching between VIV Light and Deep Dark themes.
- **Theme Persistence**: Preference is automatically saved to `localStorage` and respects system color scheme defaults.
- **Adaptive Components**: All UI elements including modals, inputs, and warning banners dynamically adjust their color palettes for optimal visibility.
- **Readability Refinements**: Removed all hardcoded "white stripes" and slate colors, replacing them with theme-aware CSS variables for a consistent high-contrast experience.
- **Consistent Branding**: Maintained core VIV design tokens while expanding the system to support a premium high-contrast dark experience.

## v0.1.6 (2026-01-12)

### Clone & TTL Refinement
- **Fixed VOD TTLs**: Standardized all VOD content to a strict 365-day (31536000s) cache TTL.
- **Optimized Live TTLs**: Implemented granular TTLs for Live HLS (Master: 1d, Playlist: 2s, Chunks: 365d).
- **Enhanced Service Cloning**: SSL Certificates and Dual Token (HLS) security settings are now accurately duplicated when cloning services.
- **YAML Export Parity**: Synchronized frontend YAML generation logic with backend deployment rules for full consistency.
