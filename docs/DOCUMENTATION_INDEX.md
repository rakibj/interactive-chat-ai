# Documentation Index - Per-Profile Settings System

## Quick Navigation

### 🚀 Get Started Quickly

1. **[README.md](README.md)** - Overview and quick start (START HERE)
2. **[QUICK_START.md](QUICK_START.md)** - Fast reference for running the system

### 📚 Understanding the System

1. **[PER_PROFILE_SETTINGS_SUMMARY.md](PER_PROFILE_SETTINGS_SUMMARY.md)** - Complete implementation overview
2. **[PROFILE_SETTINGS.md](PROFILE_SETTINGS.md)** - Comprehensive guide (detailed explanations)
3. **[PROFILE_SETTINGS_QUICK_REF.md](PROFILE_SETTINGS_QUICK_REF.md)** - Quick reference (one-pager)

### 🏗️ Architecture & Technical Details

1. **[ARCHITECTURE_VISUAL_GUIDE.md](ARCHITECTURE_VISUAL_GUIDE.md)** - Visual diagrams, flows, and relationships
2. **[interactive_chat/IMPLEMENTATION_SUMMARY.md](interactive_chat/IMPLEMENTATION_SUMMARY.md)** - Technical implementation details
3. **[IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md)** - What's done, what's upcoming

### 📖 Profile Information

1. **[interactive_chat/PROFILES.md](interactive_chat/PROFILES.md)** - Individual profile descriptions and instructions

### 🧪 Testing & Verification

See test files below - run to verify the system is working correctly

---

## Documentation Files (Root Level)

### [README.md](README.md)

**Purpose**: Main project overview and quick start

- What is this project?
- Quick start instructions
- Available profiles table
- Key features
- Usage examples
- Creating custom profiles

**Read this first if you're new to the project.**

### [PROFILE_SETTINGS.md](PROFILE_SETTINGS.md)

**Purpose**: Comprehensive guide to the profile settings system

- Overview of the system
- Profile configuration structure
- 6 pre-configured profiles with table
- How to use profile settings in code
- Integration with main conversation engine
- How to modify/create profiles
- Setting recommendations (timing, sensitivity, temperature, etc.)
- Testing instructions

**Read this for detailed understanding and reference.**

### [PROFILE_SETTINGS_QUICK_REF.md](PROFILE_SETTINGS_QUICK_REF.md)

**Purpose**: One-page quick reference

- The 9 settings per profile
- Example: Check current settings
- Example: List all profiles
- Example: Create new profile
- Profile characteristics table
- Key formulas and relationships
- Usage examples

**Read this when you need a quick lookup.**

### [PER_PROFILE_SETTINGS_SUMMARY.md](PER_PROFILE_SETTINGS_SUMMARY.md)

**Purpose**: Complete implementation summary

- What was implemented
- Profile configuration structure
- 6 pre-configured profiles with details
- Core components updated (TurnTaker, InterruptionManager, etc.)
- How to use the system
- Integration with ConversationEngine
- How to modify/create profiles
- Setting recommendations
- Testing status
- Next steps (optional enhancements)

**Read this for a complete understanding of what was built.**

### [ARCHITECTURE_VISUAL_GUIDE.md](ARCHITECTURE_VISUAL_GUIDE.md)

**Purpose**: Visual representation of the system

- System flow diagram
- Profile settings map
- Component integration matrix
- Timing relationships visualization
- Temperature scale
- Interruption sensitivity scale
- TurnTaker state diagram
- Data structure examples
- File organization
- Key relationships

**Read this to understand the visual architecture and how components relate.**

### [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md)

**Purpose**: Checklist of what's been implemented

- Completed items (✓)
- Partially implemented items
- Future enhancements (optional)
- Verification results
- Getting started instructions
- Performance characteristics
- Key benefits
- Implementation quality
- Integration status

**Read this to see what's done and what's planned.**

### [QUICK_START.md](QUICK_START.md)

**Purpose**: Fast startup guide for immediate use

- Installation steps
- Running the system
- Switching profiles
- Creating custom profiles
- Running tests
- Common commands

**Read this to get running immediately.**

---

## Documentation Files (interactive_chat/ Subdirectory)

### [interactive_chat/PROFILES.md](interactive_chat/PROFILES.md)

**Purpose**: Detailed descriptions of each profile

- Profile 1: Negotiator (Buyer)
- Profile 2: IELTS Speaking Instructor
- Profile 3: Confused Customer
- Profile 4: Technical Support Agent
- Profile 5: English Language Tutor
- Profile 6: Curious Friend

**Read this to understand each profile's behavior and settings.**

### [interactive_chat/IMPLEMENTATION_SUMMARY.md](interactive_chat/IMPLEMENTATION_SUMMARY.md)

**Purpose**: Technical implementation details

- How the system works internally
- Component descriptions
- Code structure
- Data flow
- Configuration handling
- Integration points

**Read this for deep technical understanding.**

### [interactive_chat/README.md](interactive_chat/README.md)

**Purpose**: Package-level documentation

- Module overview
- What's in interactive_chat/
- Component breakdown
- How to use the package

**Read this to understand the package structure.**

---

## How to Choose Which Document to Read

### I want to...

**...get started quickly**
→ [README.md](README.md) → [QUICK_START.md](QUICK_START.md)

**...understand what a profile is**
→ [PROFILE_SETTINGS.md](PROFILE_SETTINGS.md) → [interactive_chat/PROFILES.md](interactive_chat/PROFILES.md)

**...see all available profiles and their settings**
→ Run `python test_profiles.py` or read [PER_PROFILE_SETTINGS_SUMMARY.md](PER_PROFILE_SETTINGS_SUMMARY.md)

**...create a new profile**
→ [PROFILE_SETTINGS_QUICK_REF.md](PROFILE_SETTINGS_QUICK_REF.md) (Example section)

**...modify an existing profile**
→ [PROFILE_SETTINGS.md](PROFILE_SETTINGS.md) (Modifying Profiles section)

**...understand the architecture**
→ [ARCHITECTURE_VISUAL_GUIDE.md](ARCHITECTURE_VISUAL_GUIDE.md) → [interactive_chat/IMPLEMENTATION_SUMMARY.md](interactive_chat/IMPLEMENTATION_SUMMARY.md)

**...learn about per-profile timing**
→ [PROFILE_SETTINGS.md](PROFILE_SETTINGS.md) (Setting Recommendations section) → [ARCHITECTURE_VISUAL_GUIDE.md](ARCHITECTURE_VISUAL_GUIDE.md) (Timing Visualization)

**...understand interruption sensitivity**
→ [PROFILE_SETTINGS.md](PROFILE_SETTINGS.md) → [ARCHITECTURE_VISUAL_GUIDE.md](ARCHITECTURE_VISUAL_GUIDE.md) (Interruption Sensitivity Scale)

**...see what's implemented**
→ [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md)

**...run tests**
→ [QUICK_START.md](QUICK_START.md) (Testing section) or [PER_PROFILE_SETTINGS_SUMMARY.md](PER_PROFILE_SETTINGS_SUMMARY.md) (Testing section)

---

## Test Files

Located in project root - run these to verify the system:

### [test_profiles.py](test_profiles.py)

Lists all 6 profiles with their complete settings.

```bash
python test_profiles.py
```

### [test_settings_system.py](test_settings_system.py)

Comprehensive system test (5 test groups).

```bash
python test_settings_system.py
```

### [test_e2e_integration.py](test_e2e_integration.py)

End-to-end integration test - verifies all components work together.

```bash
python test_e2e_integration.py
```

### [test_main_profiles.py](test_main_profiles.py)

Tests that main.py loads profiles correctly.

```bash
python test_main_profiles.py
```

---

## Configuration File

### [interactive_chat/config.py](interactive_chat/config.py)

**This is where all profile settings are defined.**

Key elements:

- `INSTRUCTION_PROFILES` dict - All 6 profiles with their settings
- `get_profile_settings()` - Helper function
- `get_system_prompt()` - Helper function
- `ACTIVE_PROFILE` - Currently active profile (line ~20)

To switch profiles: Edit line ~20 and change `ACTIVE_PROFILE`.

---

## Main Application File

### [interactive_chat/main.py](interactive_chat/main.py)

**This is where everything comes together.**

Key class: `ConversationEngine`

- Loads profile settings
- Applies to all components
- Orchestrates the conversation
- Displays profile info at startup

Run with:

```bash
python -m interactive_chat.main
```

---

## Documentation Reading Path

### Path 1: Quick Start (5 minutes)

1. README.md - Get oriented
2. Run `python test_profiles.py` - See all profiles
3. Run `python -m interactive_chat.main` - Try it out

### Path 2: Understanding (30 minutes)

1. PROFILE_SETTINGS_QUICK_REF.md - Quick reference
2. PROFILE_SETTINGS.md - Detailed guide
3. interactive_chat/PROFILES.md - Profile descriptions
4. Run tests to verify understanding

### Path 3: Deep Dive (1 hour)

1. PER_PROFILE_SETTINGS_SUMMARY.md - Complete overview
2. ARCHITECTURE_VISUAL_GUIDE.md - Visual architecture
3. interactive_chat/IMPLEMENTATION_SUMMARY.md - Technical details
4. IMPLEMENTATION_CHECKLIST.md - What's implemented
5. Read source code (config.py, main.py, core/)

### Path 4: Development (As needed)

1. Choose relevant document based on task
2. Use as reference while coding
3. Run tests after changes
4. Update relevant docs if making changes

---

## Key Concepts Quick Reference

### Profile

A conversation role with independent settings (e.g., "IELTS instructor", "confused customer")

### Settings

9 customizable parameters per profile:

- name, start, voice, max_tokens, temperature, pause_ms, end_ms, safety_timeout_ms, interruption_sensitivity

### ACTIVE_PROFILE

The profile currently in use. Change it in config.py to switch profiles.

### get_profile_settings(profile_name)

Function that returns all settings for a profile (merges profile + defaults).

### TurnTaker

Component that decides when a turn ends (uses pause_ms, end_ms, safety_timeout_ms from profile).

### InterruptionManager

Component that decides if human should interrupt AI (uses interruption_sensitivity from profile).

### ConversationEngine

Main orchestration class that loads profile settings and applies them to all components.

---

## Documentation Statistics

- **Total documents**: 10
- **Root level**: 7 documents
- **In interactive_chat/**: 3 documents
- **Test files**: 4 files
- **Configuration files**: 1 file (config.py)
- **Main file**: 1 file (main.py)

---

## How Documentation is Organized

```
By Purpose:
├── Quick Start: README.md, QUICK_START.md
├── Learning: PROFILE_SETTINGS.md, PROFILE_SETTINGS_QUICK_REF.md
├── Reference: PER_PROFILE_SETTINGS_SUMMARY.md, PROFILE_SETTINGS_QUICK_REF.md
├── Architecture: ARCHITECTURE_VISUAL_GUIDE.md, IMPLEMENTATION_SUMMARY.md
├── Details: PROFILES.md, IMPLEMENTATION_CHECKLIST.md
└── Verification: Test files

By Audience:
├── New Users: README.md → QUICK_START.md
├── Learners: PROFILE_SETTINGS.md → ARCHITECTURE_VISUAL_GUIDE.md
├── Reference Users: PROFILE_SETTINGS_QUICK_REF.md
├── Developers: IMPLEMENTATION_SUMMARY.md → Code
└── Verifiers: Test files, IMPLEMENTATION_CHECKLIST.md
```

---

## Getting Help

1. **What does X do?** → Search PROFILE_SETTINGS.md or ARCHITECTURE_VISUAL_GUIDE.md
2. **How do I create a profile?** → PROFILE_SETTINGS_QUICK_REF.md (Example section)
3. **How do I modify a profile?** → PROFILE_SETTINGS.md (Modifying section)
4. **Is the system working?** → Run test_e2e_integration.py
5. **What profiles are available?** → Run test_profiles.py
6. **What was implemented?** → IMPLEMENTATION_CHECKLIST.md
7. **How does it all fit together?** → ARCHITECTURE_VISUAL_GUIDE.md

---

**Last Updated**: After per-profile settings implementation
**Status**: Complete and ready for use ✓
**All Tests Passing**: Yes (5/5 groups) ✓
