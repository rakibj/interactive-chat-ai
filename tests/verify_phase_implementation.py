#!/usr/bin/env python3
"""
Phase Visuals Implementation Verification Script
Checks that all components are in place and properly connected
"""

import os
import re
from pathlib import Path


def check_file_exists(filepath, description):
    """Check if file exists and report status"""
    exists = os.path.exists(filepath)
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {filepath}")
    return exists


def check_file_contains(filepath, search_pattern, description):
    """Check if file contains specific pattern"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            found = bool(re.search(search_pattern, content, re.IGNORECASE))
            status = "✅" if found else "❌"
            print(f"{status} {description}")
            return found
    except Exception as e:
        print(f"❌ {description} (Error: {e})")
        return False


def main():
    print("=" * 70)
    print("PHASE VISUALS IMPLEMENTATION VERIFICATION")
    print("=" * 70)
    
    # Base path
    base_path = Path(__file__).parent.parent
    
    print("\n1. CHECKING FILE EXISTENCE")
    print("-" * 70)
    
    files_to_check = [
        ("public/js/enhanced_ui.js", "Enhanced UI Manager Module"),
        ("public/js/app_live.js", "Live App Integration"),
        ("public/js/ui.js", "Basic UI Manager"),
        ("public/css/styles_modern.css", "Modern Styling"),
        ("public/index.html", "HTML Index"),
        ("interactive_chat/config.py", "Phase Configuration"),
        ("interactive_chat/server.py", "API Server"),
    ]
    
    all_exist = all(check_file_exists(base_path / f[0], f[1]) for f in files_to_check)
    
    print("\n2. CHECKING JAVASCRIPT MODULES")
    print("-" * 70)
    
    # Check enhanced_ui.js
    enhanced_ui_path = base_path / "public/js/enhanced_ui.js"
    if enhanced_ui_path.exists():
        with open(enhanced_ui_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            check1 = "class PhaseVisualsManager" in content
            check2 = "class TurnSummaryManager" in content
            check3 = "window.PhaseVisualsManager" in content
            check4 = "window.TurnSummaryManager" in content
            
            print(f"  {'✅' if check1 else '❌'} PhaseVisualsManager class defined")
            print(f"  {'✅' if check2 else '❌'} TurnSummaryManager class defined")
            print(f"  {'✅' if check3 else '❌'} PhaseVisualsManager exported to window")
            print(f"  {'✅' if check4 else '❌'} TurnSummaryManager exported to window")
            
            all_exist = all_exist and check1 and check2 and check3 and check4
    
    print("\n3. CHECKING SCRIPT INTEGRATION")
    print("-" * 70)
    
    index_path = base_path / "public/index.html"
    if index_path.exists():
        with open(index_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            # Check script tags
            has_ui_js = 'src="js/ui.js"' in content or "src='js/ui.js'" in content
            has_enhanced_js = 'src="js/enhanced_ui.js"' in content or "src='js/enhanced_ui.js'" in content
            has_app_live = 'src="js/app_live.js"' in content or "src='js/app_live.js'" in content
            
            print(f"  {'✅' if has_ui_js else '❌'} ui.js script tag present")
            print(f"  {'✅' if has_enhanced_js else '❌'} enhanced_ui.js script tag present")
            print(f"  {'✅' if has_app_live else '❌'} app_live.js script tag present")
            
            # Check script order
            ui_pos = content.find('ui.js')
            enh_pos = content.find('enhanced_ui.js')
            app_pos = content.find('app_live.js')
            
            if all(pos > 0 for pos in [ui_pos, enh_pos, app_pos]):
                order_correct = ui_pos < enh_pos < app_pos
                print(f"  {'✅' if order_correct else '❌'} Scripts in correct order (ui → enhanced → app)")
            
            # Check HTML elements
            has_phase_tracker = 'id="phase-tracker"' in content
            has_turn_summary = 'id="turn-summary"' in content
            has_phase_section = 'class="phase-section"' in content
            
            print(f"  {'✅' if has_phase_tracker else '❌'} #phase-tracker element exists")
            print(f"  {'✅' if has_turn_summary else '❌'} #turn-summary element exists")
            print(f"  {'✅' if has_phase_section else '❌'} .phase-section element exists")
            
            all_exist = all_exist and all([
                has_ui_js, has_enhanced_js, has_app_live,
                has_phase_tracker, has_turn_summary, has_phase_section
            ])
    
    print("\n4. CHECKING STYLING")
    print("-" * 70)
    
    css_path = base_path / "public/css/styles_modern.css"
    if css_path.exists():
        with open(css_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            css_checks = [
                (".phase-item", "Phase item styling"),
                (".timeline-track", "Timeline track styling"),
                (".timeline-progress", "Timeline progress styling"),
                (".turn-summary-", "Turn summary styling"),
                (".turn-details-modal", "Turn details modal"),
                (".phase-details-modal", "Phase details modal"),
            ]
            
            css_ok = True
            for selector, desc in css_checks:
                found = selector in content
                print(f"  {'✅' if found else '❌'} {desc} ({selector})")
                css_ok = css_ok and found
            
            # Count lines added
            lines = len(content.split('\n'))
            print(f"  📊 Total CSS lines: {lines}")
            
            all_exist = all_exist and css_ok
    
    print("\n5. CHECKING APP INTEGRATION")
    print("-" * 70)
    
    app_path = base_path / "public/js/app_live.js"
    if app_path.exists():
        with open(app_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            check1 = "turn.transcript" in content
            check2 = "PhaseVisualsManager" in content
            check3 = "TurnSummaryManager" in content
            check4 = "this.lastState = state" in content
            
            print(f"  {'✅' if check1 else '❌'} Using correct turn.transcript field")
            print(f"  {'✅' if check2 else '❌'} Calling PhaseVisualsManager")
            print(f"  {'✅' if check3 else '❌'} Calling TurnSummaryManager")
            print(f"  {'✅' if check4 else '❌'} Storing lastState for modal access")
            
            all_exist = all_exist and all([check1, check2, check3, check4])
    
    print("\n6. CHECKING CONFIGURATION")
    print("-" * 70)
    
    config_path = base_path / "interactive_chat/config.py"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            has_phase_profiles = "PHASE_PROFILES" in content
            has_active_profile = "ACTIVE_PHASE_PROFILE" in content
            has_ielts = "ielts_full_exam" in content
            
            print(f"  {'✅' if has_phase_profiles else '❌'} PHASE_PROFILES dictionary defined")
            print(f"  {'✅' if has_active_profile else '❌'} ACTIVE_PHASE_PROFILE setting defined")
            print(f"  {'✅' if has_ielts else '❌'} IELTS profile configuration present")
            
            all_exist = all_exist and all([has_phase_profiles, has_active_profile, has_ielts])
    
    print("\n7. CHECKING API SERVER")
    print("-" * 70)
    
    server_path = base_path / "interactive_chat/server.py"
    if server_path.exists():
        with open(server_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            check1 = "def get_full_state()" in content
            check2 = "phase_progress" in content
            check3 = "ConversationState" in content
            check4 = '"/api/state"' in content
            
            print(f"  {'✅' if check1 else '❌'} get_full_state() function defined")
            print(f"  {'✅' if check2 else '❌'} phase_progress building logic present")
            print(f"  {'✅' if check3 else '❌'} ConversationState model used")
            print(f"  {'✅' if check4 else '❌'} /api/state endpoint implemented")
            
            all_exist = all_exist and all([check1, check2, check3, check4])
    
    print("\n" + "=" * 70)
    if all_exist:
        print("✅ ALL CHECKS PASSED - Implementation is complete!")
        print("\nNext steps:")
        print("  1. Start the app: python run_html_app.py")
        print("  2. Open http://localhost:7860")
        print("  3. Check browser console for logs")
        print("  4. Phase visuals should appear in info panel")
        print("\nIf still not working:")
        print("  1. Open http://localhost:7860/diagnostic.html")
        print("  2. Run all 5 tests")
        print("  3. Share results if tests fail")
    else:
        print("❌ SOME CHECKS FAILED - Review output above")
        print("\nIssues to fix:")
        print("  - Ensure all files exist in correct locations")
        print("  - Check script loading order in HTML")
        print("  - Verify module exports to window object")
        print("  - Look for syntax errors in console")
    
    print("=" * 70)
    return 0 if all_exist else 1


if __name__ == "__main__":
    exit(main())
