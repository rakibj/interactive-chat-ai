#!/usr/bin/env python3
"""
Simulated Interruption Logic Test
---------------------------------
Verifies that the InterruptionManager correctly allows or forbids 
interruptions based on the active 'Authority' mode (Human vs AI).
"""
import os
import sys
import unittest

# Ensure project root is in path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "interactive_chat"))

from interactive_chat.core.interruption_manager import InterruptionManager


class TestInterruptionLogic(unittest.TestCase):
    
    def setUp(self):
        self.manager = InterruptionManager()
        print(f"\n🧪 SETUP: Created InterruptionManager")

    def test_human_authority_allows_interruption(self):
        """
        Scenario: Authority = 'human' (Open Mic)
        Expected: 
        - can_listen_continuously -> True
        - should_interrupt -> True (when speech/energy detected)
        """
        print(f"\n📋 TEST: Human Authority (Open Mic)")
        
        # 1. Configure
        self.manager.set_profile_settings(sensitivity=0.5, authority="human")
        print("   Config: authority='human', sensitivity=0.5")
        
        # 2. Check Hearing Permission
        # Even if AI is speaking, we should be listening for interruptions
        can_listen = self.manager.can_listen_continuously(ai_speaking=True)
        print(f"   [Check] Can listen while AI speaks? {can_listen}")
        self.assertTrue(can_listen, "Human authority should keep mic open")
        
        # 3. Check Interruption Trigger
        # Simulate user shouting "Stop"
        should_int, reason = self.manager.should_interrupt(
            ai_speaking=True,
            current_time=100.0,
            energy_condition=True,
            detected_words="Stop please"
        )
        print(f"   [Check] Should interrupt? {should_int} (Reason: {reason})")
        self.assertTrue(should_int, "User should be able to interrupt in Human mode")
        # In hybrid mode (sensitivity=0.5), output is "energy + speech...", 
        # whereas "speech detected" is for strict speech mode.
        # Just check for "speech" to cover both.
        self.assertIn("speech", reason)

    def test_ai_authority_blocks_interruption(self):
        """
        Scenario: Authority = 'ai' (Closed Mic)
        Expected:
        - can_listen_continuously -> False (Mic 'closed' while AI speaks)
        - is_turn_processing_allowed -> False
        - should_interrupt -> False (Safeguard)
        """
        print(f"\n📋 TEST: AI Authority (Closed Mic)")
        
        # 1. Configure
        self.manager.set_profile_settings(sensitivity=0.5, authority="ai")
        print("   Config: authority='ai'")
        
        # 2. Check Hearing Permission
        # When AI is speaking, mic should be ignored
        can_listen = self.manager.can_listen_continuously(ai_speaking=True)
        print(f"   [Check] Can listen while AI speaks? {can_listen}")
        self.assertFalse(can_listen, "AI authority should IGNORE mic while speaking")
        
        # 3. Check Processing Permission
        # If a turn somehow got processed, it should be rejected
        allowed = self.manager.is_turn_processing_allowed(ai_speaking=True)
        print(f"   [Check] Allow turn processing? {allowed}")
        self.assertFalse(allowed, "AI authority should reject turns while speaking")

        # 4. Check Interruption Safeguard
        # If we manually call should_interrupt, it should explicitly say NO
        should_int, reason = self.manager.should_interrupt(
            ai_speaking=True, 
            current_time=100.0, 
            energy_condition=True,
            detected_words="Stop"
        )
        print(f"   [Check] Should interrupt? {should_int} (Reason: {reason})")
        self.assertFalse(should_int, "AI authority safeguard should return False")
        self.assertEqual(reason, "authority is ai")

    def test_ai_authority_allows_listening_when_silent(self):
        """
        Scenario: Authority = 'ai' BUT AI is silent
        Expected: Mic is Open (User can take the floor)
        """
        print(f"\n📋 TEST: AI Authority (AI Silent)")
        
        self.manager.set_profile_settings(sensitivity=0.5, authority="ai")
        
        # AI finished speaking
        can_listen = self.manager.can_listen_continuously(ai_speaking=False)
        print(f"   [Check] Can listen when AI is silent? {can_listen}")
        self.assertTrue(can_listen, "Mic should open when AI stops speaking")


if __name__ == "__main__":
    unittest.main(verbosity=0)
