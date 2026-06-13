#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CLI test script - core functionality verification"""

import sys


def test_imports():
    """Test all core modules can be imported."""
    print("\n" + "="*50)
    print("Test 1: Module Imports")
    print("="*50)
    
    modules = [
        ("core.router", "need_vision"),
        ("core.context", "ContextManager"),
        ("services.asr_client", "ASRClient"),
        ("services.llm_client", "LLMClient"),
        ("services.vlm_client", "VLMClient"),
        ("utils.error_handler", "get_fallback_response"),
    ]
    
    passed = 0
    for mod, cls in modules:
        try:
            __import__(mod)
            print("[PASS] {} - {}".format(mod, cls))
            passed += 1
        except Exception as e:
            print("[FAIL] {} - {}".format(mod, str(e)))
    
    return passed == len(modules)


def test_routing():
    """Test routing logic."""
    print("\n" + "="*50)
    print("Test 2: Routing Logic")
    print("="*50)
    
    from core.router import need_vision
    
    tests = [
        ("这是什么", True),
        ("看一下", True),
        ("今天天气", False),
        ("几点了", False),
    ]
    
    passed = 0
    for text, expected in tests:
        result = need_vision(text)
        if result == expected:
            print("[PASS] need_vision('{}') = {}".format(text, result))
            passed += 1
        else:
            print("[FAIL] need_vision('{}') = {} (expected {})".format(text, result, expected))
    
    return passed == len(tests)


def test_context():
    """Test context management."""
    print("\n" + "="*50)
    print("Test 3: Context Management")
    print("="*50)
    
    from core.context import ContextManager
    
    ctx = ContextManager(max_rounds=2)
    ctx.add("user", "q1")
    ctx.add("assistant", "a1")
    ctx.add("user", "q2")
    ctx.add("assistant", "a2")
    ctx.add("user", "q3")
    ctx.add("assistant", "a3")
    
    history = ctx.get()
    if len(history) == 4:
        print("[PASS] Context limit works (4 items for max_rounds=2)")
        return True
    else:
        print("[FAIL] Expected 4 items, got {}".format(len(history)))
        return False


def test_fallback():
    """Test fallback responses."""
    print("\n" + "="*50)
    print("Test 4: Fallback Responses")
    print("="*50)
    
    from utils.error_handler import get_fallback_response
    
    reply = get_fallback_response("")
    if reply and len(reply) > 0:
        print("[PASS] Fallback reply generated: {}...".format(reply[:30]))
        return True
    else:
        print("[FAIL] Fallback reply is empty")
        return False


def test_pipeline():
    """Test AppPipeline."""
    print("\n" + "="*50)
    print("Test 5: AppPipeline")
    print("="*50)
    
    try:
        from core.pipeline import AppPipeline
        pipeline = AppPipeline()
        print("[PASS] AppPipeline initialized")
        print("  - Context: {}".format("OK" if pipeline.ctx else "FAIL"))
        print("  - ASR: {}".format("OK" if pipeline._asr else "FAIL"))
        print("  - LLM: {}".format("OK" if pipeline._llm else "FAIL"))
        print("  - VLM: {}".format("OK" if pipeline._vlm else "FAIL"))
        print("  - TTS: {}".format("OK" if pipeline._tts else "FAIL"))
        return True
    except Exception as e:
        print("[FAIL] {}".format(str(e)))
        return False


def main():
    """Run all tests."""
    print("\n" + "="*50)
    print("  CLI Test Suite - Core Functionality")
    print("="*50)
    
    tests = [
        ("Imports", test_imports),
        ("Routing", test_routing),
        ("Context", test_context),
        ("Fallback", test_fallback),
        ("Pipeline", test_pipeline),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print("[ERROR] {}: {}".format(name, str(e)))
            results.append((name, False))
    
    print("\n" + "="*50)
    print("Test Summary")
    print("="*50)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print("[{}] {}".format(status, name))
    
    print("\nTotal: {}/{} passed".format(passed, total))
    
    if passed == total:
        print("\n[SUCCESS] All core features verified!")
        return 0
    else:
        print("\n[FAILURE] Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
