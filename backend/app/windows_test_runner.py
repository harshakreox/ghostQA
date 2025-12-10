"""
Windows-compatible test runner with WebSocket logging
"""

import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import List
from models import TestCase, TestReport
import queue
import threading


def run_tests_windows_safe(
    test_cases: List[TestCase],
    base_url: str,
    report_dir: str,
    headless: bool,
    main_loop,
    broadcast_func
) -> TestReport:
    """
    Run tests in Windows-compatible way with WebSocket logging.
    """
    
    # Thread-safe log queue
    log_queue = queue.Queue()
    
    def thread_safe_log(message: str):
        """Log that works across threads and broadcasts to WebSocket"""
        # Print to console for debugging
        print(f"[TEST] {message}")
        
        # Send to WebSocket via main event loop
        try:
            future = asyncio.run_coroutine_threadsafe(
                broadcast_func(message),
                main_loop
            )
            # Don't wait for result to avoid blocking
        except Exception as e:
            print(f"[WARNING] Failed to broadcast log: {e}")
    
    def execute_in_thread():
        """Execute tests in separate thread with correct event loop"""
        
        thread_safe_log("=" * 60)
        thread_safe_log(" WINDOWS TEST RUNNER - Starting")
        thread_safe_log("=" * 60)
        
        try:
            # Set Windows event loop policy
            if sys.platform == 'win32':
                thread_safe_log(" Setting Windows ProactorEventLoop policy...")
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            
            # Create new event loop
            thread_safe_log(" Creating new event loop...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            thread_safe_log(" Event loop created successfully")
            
            try:
                # Import test engine
                thread_safe_log(" Importing TestEngine...")
                from test_engine import TestEngine
                
                # Create engine with our thread-safe logger
                thread_safe_log(f" Creating TestEngine (headless={headless})...")
                engine = TestEngine(log_callback=thread_safe_log)
                
                thread_safe_log(f" Running {len(test_cases)} test cases...")
                thread_safe_log("-" * 60)
                
                # Run tests
                result = loop.run_until_complete(
                    engine.run_tests(
                        test_cases=test_cases,
                        base_url=base_url,
                        report_dir=report_dir,
                        headless=headless
                    )
                )
                
                thread_safe_log("-" * 60)
                thread_safe_log(f"[OK] Tests completed successfully!")
                thread_safe_log(f"   Passed: {result.passed}")
                thread_safe_log(f"   Failed: {result.failed}")
                thread_safe_log(f"   Duration: {result.duration:.2f}s")
                thread_safe_log("=" * 60)
                
                return result
                
            except Exception as e:
                thread_safe_log("=" * 60)
                thread_safe_log("[ERR] ERROR IN TEST EXECUTION:")
                thread_safe_log("=" * 60)
                thread_safe_log(f"Error: {str(e)}")
                thread_safe_log("")
                thread_safe_log("Full traceback:")
                import traceback
                for line in traceback.format_exc().split('\n'):
                    if line.strip():
                        thread_safe_log(line)
                thread_safe_log("=" * 60)
                raise
                
            finally:
                thread_safe_log(" Closing event loop...")
                loop.close()
                
        except Exception as e:
            thread_safe_log("=" * 60)
            thread_safe_log("[ERR] CRITICAL ERROR IN WORKER THREAD:")
            thread_safe_log("=" * 60)
            thread_safe_log(f"Error: {str(e)}")
            import traceback
            for line in traceback.format_exc().split('\n'):
                if line.strip():
                    thread_safe_log(line)
            thread_safe_log("=" * 60)
            raise
    
    # Run in thread pool
    print("\n Submitting test execution to thread pool...")
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(execute_in_thread)
        result = future.result()
        print("[OK] Thread execution completed\n")
        return result