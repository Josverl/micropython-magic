"""Test memory info log format parsing for both standard and decorator formats."""

import re
import pytest


def test_meminfo_start_regex_patterns():
    """Test that RE_MEM_INFO_START regex handles both standard and decorator formats."""
    from micropython_magic.memoryinfo import RE_MEM_INFO_START
    
    # Test cases: (input_string, expected_captured_name)
    test_cases = [
        # Standard format (original)
        ("*** Memory info before_test ***", "before_test"),
        ("*** Memory info test123 ***", "test123"),
        ("*** Memory info ***", ""),  # Edge case: no name
        
        # Decorator format with colon (the issue being fixed)
        ("*** Memory info: before_test ***", "before_test"),
        ("*** Memory info: after_test ***", "after_test"),
        ("*** Memory info:test456 ***", "test456"),  # No space after colon
        
        # Mixed formats (space before colon)
        ("*** Memory info : mixed_test ***", "mixed_test"),
        ("*** Memory info  test_spaces ***", "test_spaces"),  # Multiple spaces
        
        # Additional punctuation and textual variations (new requirement)
        ("*** Memory info:  extra_spaces ***", "extra_spaces"),  # Extra spaces after colon
        ("*** Memory info   :   test ***", "test"),  # Spaces around colon
        ("*** Memory info:my_function ***", "my_function"),  # No spaces at all
        ("*** Memory info  :test_name ***", "test_name"),  # Spaces before, not after
        ("*** Memory info: test-with-dashes ***", "test-with-dashes"),  # Dashes in name
        ("*** Memory info: test_with_123 ***", "test_with_123"),  # Numbers in name
        ("*** Memory info: CamelCaseTest ***", "CamelCaseTest"),  # CamelCase
    ]
    
    for test_str, expected in test_cases:
        match = RE_MEM_INFO_START.match(test_str)
        assert match is not None, f"Failed to match: {test_str}"
        captured = match.group(1)
        assert captured == expected, f"For '{test_str}': expected '{expected}', got '{captured}'"


def test_meminfo_end_regex_pattern():
    """Test that RE_MEM_INFO_END regex works as expected."""
    from micropython_magic.memoryinfo import RE_MEM_INFO_END
    
    # Standard end marker
    end_marker = "*********************"
    match = RE_MEM_INFO_END.match(end_marker)
    assert match is not None, "Failed to match end marker"


def test_parse_log_with_decorator_format():
    """Test parsing a complete log with decorator format."""
    from micropython_magic.memoryinfo import MemoryInfoList
    
    # Sample log with decorator format
    log_lines = [
        "Some other log line",
        "*** Memory info: test_function ***",
        "GC: total: 262144, used: 12345, free: 249799",
        " No. of 1-blocks: 10, 2-blocks: 5, max blk sz: 128, max free sz: 200",
        "stack: 512 out of 8192",
        "10000: ................................",
        "*********************",
        "Another log line",
    ]
    
    mem_list = MemoryInfoList()
    result = mem_list.parse_log(log_lines)
    
    assert len(result) == 1, f"Expected 1 memory info, got {len(result)}"
    assert result[0].name == "test_function", f"Expected name 'test_function', got '{result[0].name}'"
    assert result[0].total == 262144
    assert result[0].used == 12345
    assert result[0].free == 249799


def test_parse_log_with_standard_format():
    """Test parsing a complete log with standard format (regression test)."""
    from micropython_magic.memoryinfo import MemoryInfoList
    
    # Sample log with standard format (no colon)
    log_lines = [
        "Some other log line",
        "*** Memory info test_function ***",
        "GC: total: 262144, used: 12345, free: 249799",
        " No. of 1-blocks: 10, 2-blocks: 5, max blk sz: 128, max free sz: 200",
        "stack: 512 out of 8192",
        "10000: ................................",
        "*********************",
        "Another log line",
    ]
    
    mem_list = MemoryInfoList()
    result = mem_list.parse_log(log_lines)
    
    assert len(result) == 1, f"Expected 1 memory info, got {len(result)}"
    assert result[0].name == "test_function", f"Expected name 'test_function', got '{result[0].name}'"
    assert result[0].total == 262144
    assert result[0].used == 12345
    assert result[0].free == 249799


def test_parse_log_with_multiple_entries():
    """Test parsing a log with multiple memory info entries in both formats."""
    from micropython_magic.memoryinfo import MemoryInfoList
    
    log_lines = [
        "Start of log",
        "*** Memory info before_test ***",
        "GC: total: 262144, used: 10000, free: 252144",
        " No. of 1-blocks: 5, 2-blocks: 3, max blk sz: 64, max free sz: 100",
        "stack: 256 out of 8192",
        "10000: ................................",
        "*********************",
        "Some processing...",
        "*** Memory info: after_test ***",
        "GC: total: 262144, used: 20000, free: 242144",
        " No. of 1-blocks: 15, 2-blocks: 8, max blk sz: 128, max free sz: 150",
        "stack: 512 out of 8192",
        "10000: TTTTTTTT........................",
        "*********************",
        "End of log",
    ]
    
    mem_list = MemoryInfoList()
    result = mem_list.parse_log(log_lines)
    
    assert len(result) == 2, f"Expected 2 memory info entries, got {len(result)}"
    assert result[0].name == "before_test"
    assert result[0].used == 10000
    assert result[1].name == "after_test"
    assert result[1].used == 20000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
