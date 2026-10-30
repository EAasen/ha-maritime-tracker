# Norwegian Maritime Tracker - v1.2.0 Documentation Index

Welcome to the Norwegian Maritime Tracker for Home Assistant! This document helps you navigate all available resources.

**Current Version:** 1.2.0  
**Minimum HA Version:** 2025.1.0  
**Status:** Production Ready ✅

---

## 🚀 Quick Start

**First time installing?** Start here:

1. [Installation Guide](docs/installation.md) - Step-by-step setup
2. [Configuration Guide](docs/configuration.md) - Getting your first area set up
3. [Usage Guide](docs/usage.md) - How to use the integration

**Already installed and testing?** Jump to:

- [Testing Guide](docs/TESTING_GUIDE.md) - Complete testing procedures for development and HAOS
- [Troubleshooting](docs/troubleshooting.md) - If something isn't working

---

## 📚 Complete Documentation

### User Guides (For End Users)

| Document | Purpose |
|----------|---------|
| [Installation Guide](docs/installation.md) | HACS setup, manual installation, first-time configuration |
| [Configuration Guide](docs/configuration.md) | All configuration options explained with examples |
| [Usage Guide](docs/usage.md) | Using entities, creating automations, Lovelace card setup |
| [Troubleshooting Guide](docs/troubleshooting.md) | Common issues and solutions, debug mode, log analysis |

### Developer & Technical Guides (For Developers)

| Document | Purpose |
|----------|---------|
| [Architecture Documentation](docs/architecture.md) | Integration design, data flow, component overview |
| [Development Guide](docs/development.md) | Setting up dev environment, coding standards, testing |
| [Testing Guide](docs/TESTING_GUIDE.md) | **NEW** - Complete testing procedures (33+ test modules) |
| [Development Phases](docs/DEVELOPMENT_PHASES.md) | **NEW** - Historical overview of all 5 development phases |

### Reference Materials (For Everyone)

| Document | Purpose |
|----------|---------|
| [Feature Backlog](docs/FEATURE_BACKLOG.md) | Planned features and roadmap for future versions |
| [Project Status](docs/PROJECT_STATUS.md) | Current status, milestones, and progress |
| [Documentation Index](docs/DOCUMENTATION_INDEX.md) | Master index of all documentation |
| [Documentation Summary](docs/DOCUMENTATION_SUMMARY.md) | Quick reference guide |

### Phase Documentation (Historical Reference)

Development was organized in 5 phases. For detailed phase information:

| Phase | Files |
|-------|-------|
| **Phase 1-2: Core Foundation** | [Test Guide](docs/PHASE_1_2_TEST_GUIDE.md) |
| **Phase 3: Watchlist** | [Test Guide](docs/PHASE_3_TEST_GUIDE.md), [Summary](docs/PHASE_3_FINAL_SUMMARY.md) |
| **Phase 4: Dashboard** | [Test Guide](docs/PHASE_4_TEST_GUIDE.md), [Summary](docs/PHASE_4_IMPLEMENTATION_SUMMARY.md) |
| **Phase 5: Production** | [Checklist](docs/PHASE_5_TEST_CHECKLIST.md), [Process](docs/PHASE_5_TEST_PROCESS.md), [Comprehensive Summary](docs/PHASE_5_COMPREHENSIVE_SUMMARY.md), [Quick Start](docs/PHASE_5_QUICKSTART.md), [Preparation](docs/PHASE_5_PREPARATION.md), [Complete](docs/PHASE_5_1_COMPLETE.md), [Development](docs/PHASE_5_DEVELOPMENT.md), [Session Summary](docs/PHASE_5_SESSION_SUMMARY.md) |

### Release Information

| Document | Purpose |
|----------|---------|
| [CHANGELOG.md](CHANGELOG.md) | Version history and released features |
| [Release Summary](RELEASE_SUMMARY.md) | Details about v1.2.0 release and cleanup |

---

## 🎯 Finding What You Need

### I'm installing the integration
→ [Installation Guide](docs/installation.md)

### I need to configure my area
→ [Configuration Guide](docs/configuration.md)

### I want to use all the features
→ [Usage Guide](docs/usage.md)

### I have a problem
→ [Troubleshooting Guide](docs/troubleshooting.md)

### I want to understand the design
→ [Architecture Documentation](docs/architecture.md)

### I want to contribute code
→ [Development Guide](docs/development.md)

### I want to run tests
→ [Testing Guide](docs/TESTING_GUIDE.md)

### I want historical context
→ [Development Phases](docs/DEVELOPMENT_PHASES.md)

### I want to see what's coming
→ [Feature Backlog](docs/FEATURE_BACKLOG.md)

### I need to check on something specific
→ [Full Documentation Index](docs/DOCUMENTATION_INDEX.md)

---

## 🧪 Testing Information

### Quick Test (Development)
```bash
pytest tests/ -v --cov=custom_components/marinetraffic_tracker
```

### Comprehensive Testing
Follow the [Testing Guide](docs/TESTING_GUIDE.md) which includes:
- Unit test procedures (32 test files, 33+ modules)
- Integration test workflows
- Manual HAOS testing (10-step guide)
- Performance and stress testing
- Event validation
- Error recovery testing

### Test Coverage
- **32 test files** with comprehensive coverage
- **33+ test modules** covering all functionality
- **≥80% code coverage** for core modules
- **Ruff linter**: ✅ Passing
- **MyPy type checking**: ✅ Passing
- **CI/CD pipeline**: ✅ All green

---

## 📋 Key Features

### Core Tracking
- Real-time vessel tracking in Norwegian waters
- Official Kystverket / BarentsWatch AIS feed
- Geographic area configuration (radius or bounding box)
- Automatic map markers

### Persistent Watchlist (Phase 3)
- Track up to 100 specific vessels by MMSI
- Outside configured geographic area
- No additional API calls required
- Editable through Home Assistant options

### Real-time Dashboard (Phase 4)
- Interactive Leaflet-based map card
- WebSocket API for live updates
- Vessel position trails (max 50 points)
- Course/heading indicators
- Vessel details pane
- Mobile-responsive design

### Advanced Features
- Vessel event emission (`marinetraffic_vessel_status_changed`)
- Port call tracking
- Vessel log files (CSV/JSON Lines)
- Statistics and analytics
- Entity picture support
- Multi-source preparation (v2.0.0)

---

## 🔧 System Requirements

| Requirement | Details |
|---|---|
| **Home Assistant** | 2025.1.0 or newer |
| **Network** | Internet access to Norwegian maritime APIs |
| **Credentials** | Free BarentsWatch account (takes 2 minutes) |
| **Python** | 3.11+ (built into Home Assistant) |

---

## 📞 Support

### Getting Help

1. **Check the docs first:**
   - [Troubleshooting Guide](docs/troubleshooting.md) - Most common issues
   - [Testing Guide](docs/TESTING_GUIDE.md) - Validation procedures

2. **Search existing issues:**
   - GitHub Issues: https://github.com/EAasen/ha-maritime-tracker/issues

3. **Ask the community:**
   - GitHub Discussions: https://github.com/EAasen/ha-maritime-tracker/discussions
   - Home Assistant Forums: Search for "maritime tracker"

4. **Report a bug:**
   - Create an issue with: HA version, integration version, logs, steps to reproduce

---

## 🎓 Learning Paths

### For New Users
1. [Installation Guide](docs/installation.md)
2. [Quick Start (Step 1-7)](README.md)
3. [Usage Guide](docs/usage.md)
4. [Troubleshooting](docs/troubleshooting.md)

### For Developers
1. [Architecture](docs/architecture.md)
2. [Development Guide](docs/development.md)
3. [Testing Guide](docs/TESTING_GUIDE.md)
4. [Development Phases](docs/DEVELOPMENT_PHASES.md)

### For Contributors
1. [Contributing Guide](CONTRIBUTING.md)
2. [Development Guide](docs/development.md)
3. [Testing Guide](docs/TESTING_GUIDE.md)
4. [Architecture](docs/architecture.md)

### For Migrating from Older Versions
1. [CHANGELOG](CHANGELOG.md) - See what changed
2. [Configuration Guide](docs/configuration.md) - Updated options
3. [Migration Notes](docs/DEVELOPMENT_PHASES.md#version-history) - Breaking changes

---

## 🚀 Version Information

### Current Release (v1.2.0)

**New in this release:**
- Persistent vessel watchlist with 100 MMSI capacity
- Real-time WebSocket API + interactive Leaflet dashboard card
- Complete testing framework (33+ modules)
- Comprehensive testing guide (17K words)
- Development phases documentation (12K words)
- Repository cleanup and documentation reorganization

**See:** [Release Summary](RELEASE_SUMMARY.md)

### Previous Releases

- **v1.1.0+**: Watchlist feature added
- **v1.0.0**: Initial production release

**See:** [CHANGELOG.md](CHANGELOG.md)

### Future Roadmap (v2.0.0+)

- Multi-source vessel tracking
- International waters support
- Advanced port call analytics
- Real-time route planning
- Custom filtering expressions

**See:** [Feature Backlog](docs/FEATURE_BACKLOG.md)

---

## 📊 Project Statistics

| Metric | Value |
|--------|-------|
| Documentation files | 26 in `/docs` |
| Test files | 32 |
| Test modules | 33+ |
| Code coverage | ≥80% |
| Version | 1.2.0 |
| HA minimum | 2025.1.0 |
| License | MIT |

---

## 🎯 Navigation Tips

- **Use the sidebar/menu** in your editor/viewer to jump between sections
- **CTRL+Click on links** to open in new tab
- **Search (CTRL+F)** within documents for specific terms
- **Start with README.md** if you're not sure where to go

---

## 💡 Pro Tips

1. **Enable debug logging** for troubleshooting:
   ```yaml
   logger:
     logs:
       custom_components.marinetraffic_tracker: debug
   ```

2. **Check the logs first** - Most issues are explained there
   - Settings → System → Logs (search "marinetraffic_tracker")

3. **Use Developer Tools** for testing:
   - Developer Tools → States (check sensor values)
   - Developer Tools → Events (watch for vessel events)
   - Developer Tools → Services (test integrations)

4. **Read the Testing Guide** if you want to validate everything works
   - 10 manual testing steps included
   - Covers HAOS installation testing

---

## 📝 Related Links

- **Main Repository:** https://github.com/EAasen/ha-maritime-tracker
- **GitHub Issues:** https://github.com/EAasen/ha-maritime-tracker/issues
- **GitHub Discussions:** https://github.com/EAasen/ha-maritime-tracker/discussions
- **HACS Integration:** (Available through HACS custom repositories)
- **BarentsWatch (API provider):** https://www.barentswatch.no/

---

## 📜 License

Norwegian Maritime Tracker is released under the MIT License. See [LICENSE](LICENSE) for details.

---

## ✨ Acknowledgments

Thank you to:
- The Home Assistant community for feedback and support
- Kystverket / BarentsWatch for the official AIS feed
- Contributors to testing and development

---

**Last Updated:** October 2026  
**Documentation Version:** 1.2.0  
**Status:** Complete & Production Ready ✅

For the latest information, visit: https://github.com/EAasen/ha-maritime-tracker
