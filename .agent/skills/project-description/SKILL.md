---
name: project-description
description: Maintains project_description.md with current architecture, tech stack, and implementation details. Use when making meaningful changes that alter project understanding, add features, change structure, or perform major refactors.
---

# Project Description Skill

This skill ensures `project_description.md` stays synchronized with the current state of the Interactive Chat AI project.

## When to use this skill

Update `project_description.md` when changes are **meaningful**:

✅ **Update for these changes:**
- Adding new features or capabilities
- Structural changes (new modules, refactored architecture)
- Major refactors affecting multiple components
- Changes to core algorithms or state machines
- New configuration options or profiles
- Updates to threading model or concurrency patterns
- Changes to tech stack or dependencies
- Performance optimizations that alter behavior
- New testing infrastructure

❌ **Do NOT update for these changes:**
- Bug fixes that don't change behavior
- Code style improvements or formatting
- Minor variable/function renames
- Documentation-only changes
- Log message updates
- Comment additions
- Single-line tweaks or adjustments

## File Location

**Path:** `project_description.md` (project root)

This file serves as the single source of truth for project architecture and should be referenced by other developers or AI agents working on the codebase.

## Content Structure

## Content Structure

The file should follow this structure:

```markdown
# [Project Name] - Project Summary

## Overview
Brief description of what the project does and its primary use case.

## Technology Stack

### Core Dependencies
List primary language and key libraries.

### [Domain-Specific Categories]
Group dependencies by function (e.g., ASR, TTS, VAD, LLM).

## Architecture

### Project Structure
Directory tree with brief descriptions of key files/folders.

## Core Components

### [Component Name]
For each major component:
- **Purpose**: What it does
- **Key Responsibilities**: Main functions
- **Key Methods/Properties**: Important API surface
- **Configuration**: Relevant settings

## Key Design Patterns

Document important architectural decisions:
- Threading models
- State machines
- Interruption handling
- Error handling strategies

## Critical Timing Metrics

Performance characteristics and latency breakdowns.

## Testing Infrastructure

Test files and their purposes.

## Environment Variables

Required configuration.

## Common Workflows

How to perform typical tasks (adding profiles, debugging, switching backends).

## Known Limitations

Current constraints or platform-specific issues.

## Future Enhancements

Planned improvements.
```

## Update Guidelines

### 1. Read Current State
Always read `project_description.md` before updating to understand what has changed.

### 2. Identify Affected Sections
Determine which sections need updates based on the change type:
- New feature → Update "Overview", "Core Components", add to relevant sections
- Refactor → Update "Architecture", "Core Components", "Key Design Patterns"
- Performance change → Update "Critical Timing Metrics"
- New dependency → Update "Technology Stack"

### 3. Maintain Consistency
- Use existing terminology and naming conventions
- Match the technical depth of existing content
- Keep formatting consistent (headings, code blocks, lists)
- Preserve the structure unless major reorganization is needed

### 4. Be Concise
- Focus on *what* and *why*, not *how* (code shows how)
- Use bullet points for scannability
- Include code snippets only for critical patterns
- Keep descriptions to 2-3 sentences maximum

### 5. Update Metadata
- Ensure version numbers, file paths, and line counts are accurate
- Update "Future Enhancements" if features are completed
- Move completed items from "Future" to appropriate sections

## Decision Tree

**Ask yourself:**
1. Does this change affect how someone would understand the project architecture? → **Update**
2. Does this change add/remove/modify a core component? → **Update**
3. Does this change alter the tech stack or dependencies? → **Update**
4. Is this a bug fix or minor tweak that doesn't change behavior? → **Skip**
5. When in doubt, does the change warrant updating the architectural summary? → If yes, **Update**

## Example Updates

### Adding a New Profile
**Meaningful?** Yes, if it introduces new authority mode or significantly different behavior.
**Update:** Add to "Configuration System" → "Pre-configured Profiles" list.

### Fixing a Race Condition
**Meaningful?** Yes, if it changes threading patterns or synchronization strategy.
**Update:** Update "Key Design Patterns" → "Multi-threaded Safety" section.

### Renaming a Variable
**Meaningful?** No.
**Update:** Skip.

### Adding Analytics System
**Meaningful?** Yes, new feature.
**Update:** Add "Turn Analytics System" section, update "Core Components", update "Technology Stack" if new dependencies.

## Workflow

1. **Detect meaningful change** during code review or after implementation
2. **Read current** `project_description.md`
3. **Identify sections** to update
4. **Make targeted edits** (use `multi_replace_file_content` for multiple sections)
5. **Verify accuracy** - ensure all references are current
6. **Keep concise** - remove outdated information, consolidate where possible

## Integration with Other Skills

- **brand-identity**: Use voice/tone guidelines from `voice-tone.md` when writing descriptions
- **gemini-skill-creator**: Follow documentation style (Purpose, Key Responsibilities, etc.)

## Key Reminders

- This is a **living document** - it should evolve with the project
- **Accuracy over completeness** - better to have accurate partial documentation than outdated comprehensive docs
- **Developer-focused** - write for someone who needs to understand the system quickly
- **Reference, not tutorial** - link to code, don't duplicate it
