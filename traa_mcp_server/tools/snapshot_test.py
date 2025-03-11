"""Tests for snapshot tool implementation"""

import unittest
from unittest.mock import patch, MagicMock
import numpy as np
import os
import tempfile
import shutil
import importlib.util

from mcp.server.fastmcp.utilities.types import Image
from traa import Size, Rect, Error
from traa_mcp_server.tools.snapshot import (
    enum_screen_sources, 
    create_snapshot, 
    save_snapshot, 
    SimpleScreenSourceInfo,
    _create_snapshot  # 导入内部函数用于测试
)

# Check if PIL is available
PIL_AVAILABLE = importlib.util.find_spec('PIL') is not None

class TestSnapshot(unittest.TestCase):
    """Test cases for snapshot tool implementation"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a mock screen source for testing
        self.mock_source = MagicMock()
        self.mock_source.id = 1
        self.mock_source.title = "Test Window"
        self.mock_source.is_window = True
        self.mock_source.rect = Rect(0, 0, 1920, 1080)
        
        # Create a temporary directory for file tests
        self.temp_dir = tempfile.mkdtemp()
        self.test_image_path = os.path.join(self.temp_dir, "test.png")

    def tearDown(self):
        """Clean up test fixtures"""
        # Remove temporary directory and its contents
        shutil.rmtree(self.temp_dir)

    def test_enum_screen_sources_success(self):
        """Test successful enumeration of screen sources"""
        with patch('traa.enum_screen_sources') as mock_enum:
            # Setup mock return value
            mock_enum.return_value = [self.mock_source]
            
            # Call function
            result = enum_screen_sources()
            
            # Verify results
            self.assertEqual(len(result), 1)
            source = result[0]
            self.assertIsInstance(source, SimpleScreenSourceInfo)
            self.assertEqual(source.id, 1)
            self.assertEqual(source.title, "Test Window")
            self.assertTrue(source.is_window)
            self.assertEqual(source.rect, (0, 0, 1920, 1080))

    def test_enum_screen_sources_empty(self):
        """Test enumeration when no screen sources are available"""
        with patch('traa.enum_screen_sources') as mock_enum:
            mock_enum.return_value = []
            result = enum_screen_sources()
            self.assertEqual(len(result), 0)

    def test_enum_screen_sources_error(self):
        """Test enumeration when an error occurs"""
        with patch('traa.enum_screen_sources') as mock_enum:
            mock_enum.side_effect = Error(1, "Test error")
            with self.assertRaises(RuntimeError) as context:
                enum_screen_sources()
            self.assertIn("Failed to enumerate screen sources", str(context.exception))

    def test_create_snapshot_success(self):
        """Test successful snapshot creation"""
        mock_image_data = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_size = Size(100, 100)
        
        with patch('traa.create_snapshot') as mock_snapshot:
            # Setup mock return value
            mock_snapshot.return_value = (mock_image_data, mock_size)
            
            # Call function
            result = create_snapshot(1, (100, 100))
            
            # Verify results
            self.assertIsInstance(result, Image)

    def test_create_snapshot_invalid_source_id(self):
        """Test snapshot creation with invalid source ID"""
        with self.assertRaises(ValueError):
            create_snapshot(-1, (100, 100))

    def test_create_snapshot_invalid_size(self):
        """Test snapshot creation with invalid size"""
        test_cases = [
            (0, 100),
            (100, 0),
            (-100, 100),
            (100, -100)
        ]
        
        for width, height in test_cases:
            with self.assertRaises(ValueError):
                create_snapshot(1, (width, height))

    def test_create_snapshot_traa_error(self):
        """Test snapshot creation when traa raises an error"""
        with patch('traa.create_snapshot') as mock_snapshot:
            mock_snapshot.side_effect = Error(22, "Invalid source ID")
            with self.assertRaises(RuntimeError) as context:
                create_snapshot(1, (100, 100))
            self.assertIn("Failed to create snapshot", str(context.exception))

    def test_create_snapshot_invalid_result_format(self):
        """Test snapshot creation when traa returns invalid format"""
        with patch('traa.create_snapshot') as mock_snapshot:
            mock_snapshot.return_value = None  # Invalid return value
            with self.assertRaises(RuntimeError) as context:
                create_snapshot(1, (100, 100))
            self.assertIn("Invalid result format", str(context.exception))

    @unittest.skipIf(not PIL_AVAILABLE, "PIL (Pillow) is not available")
    def test_save_snapshot_success(self):
        """Test successful saving of snapshot to file"""
        mock_image_data = np.zeros((100, 100, 4), dtype=np.uint8)  # RGBA format
        mock_size = Size(100, 100)
        
        with patch('traa.create_snapshot') as mock_snapshot:
            # Setup mock return value
            mock_snapshot.return_value = (mock_image_data, mock_size)
            
            # Test saving with different formats and quality settings
            test_cases = [
                ("test_80.jpeg", "jpeg", 80),
                ("test_100.jpeg", "jpeg", 100),
                ("test_80.png", "png", 80),
                ("test_100.png", "png", 100)
            ]
            
            for filename, fmt, quality in test_cases:
                file_path = os.path.join(self.temp_dir, filename)
                save_snapshot(1, (100, 100), file_path, quality=quality, format=fmt)
                
                # Verify file was created
                self.assertTrue(os.path.exists(file_path))
                
                # Verify file size is not zero
                self.assertGreater(os.path.getsize(file_path), 0)
                
                # Verify image format
                from PIL import Image
                with Image.open(file_path) as img:
                    self.assertEqual(img.format.lower(), fmt)

    @unittest.skipIf(not PIL_AVAILABLE, "PIL (Pillow) is not available")
    def test_save_snapshot_create_directory(self):
        """Test that save_snapshot creates parent directories if they don't exist"""
        nested_path = os.path.join(self.temp_dir, "nested", "dir", "test.jpeg")
        
        with patch('traa.create_snapshot') as mock_snapshot:
            mock_snapshot.return_value = (np.zeros((100, 100, 4), dtype=np.uint8), Size(100, 100))
            
            # Call function
            save_snapshot(1, (100, 100), nested_path, quality=80, format="jpeg")
            
            # Verify file was created in nested directory
            self.assertTrue(os.path.exists(nested_path))

    def test_save_snapshot_invalid_source_id(self):
        """Test save_snapshot with invalid source ID"""
        with self.assertRaises(ValueError):
            save_snapshot(-1, (100, 100), self.test_image_path)

    def test_save_snapshot_invalid_size(self):
        """Test save_snapshot with invalid size"""
        test_cases = [
            (0, 100),
            (100, 0),
            (-100, 100),
            (100, -100)
        ]
        
        for width, height in test_cases:
            with self.assertRaises(ValueError):
                save_snapshot(1, (width, height), self.test_image_path)

    def test_save_snapshot_invalid_format(self):
        """Test save_snapshot with invalid format"""
        with self.assertRaises(ValueError):
            save_snapshot(1, (100, 100), self.test_image_path, format="invalid")

    def test_save_snapshot_traa_error(self):
        """Test save_snapshot when traa raises an error"""
        with patch('traa.create_snapshot') as mock_snapshot:
            mock_snapshot.side_effect = Error(22, "Invalid source ID")
            with self.assertRaises(RuntimeError) as context:
                save_snapshot(1, (100, 100), self.test_image_path)
            self.assertIn("Failed to create snapshot", str(context.exception))

    @unittest.skipIf(not PIL_AVAILABLE, "PIL (Pillow) is not available")
    def test_save_snapshot_file_error(self):
        """Test save_snapshot when file operations fail"""
        # Create a directory that cannot be written to
        read_only_dir = os.path.join(self.temp_dir, "readonly")
        os.makedirs(read_only_dir)
        os.chmod(read_only_dir, 0o444)  # Read-only permission
        
        with patch('traa.create_snapshot') as mock_snapshot:
            mock_snapshot.return_value = (np.zeros((100, 100, 4), dtype=np.uint8), Size(100, 100))
            with self.assertRaises(RuntimeError) as context:
                save_snapshot(1, (100, 100), os.path.join(read_only_dir, "test.jpeg"))
            self.assertIn("Failed to save snapshot", str(context.exception))

    def test_create_snapshot_internal_success(self):
        """Test successful creation of internal snapshot"""
        mock_image_data = np.zeros((100, 100, 4), dtype=np.uint8)  # RGBA format
        mock_size = Size(100, 100)
        
        with patch('traa.create_snapshot') as mock_snapshot:
            # Setup mock return value
            mock_snapshot.return_value = (mock_image_data, mock_size)
            
            # Test JPEG format
            pil_image = _create_snapshot(1, (100, 100), "jpeg")
            self.assertEqual(pil_image.mode, "RGB")
            self.assertEqual(pil_image.size, (100, 100))
            
            # Test PNG format
            pil_image = _create_snapshot(1, (100, 100), "png")
            self.assertEqual(pil_image.mode, "RGBA")
            self.assertEqual(pil_image.size, (100, 100))

    def test_create_snapshot_internal_invalid_format(self):
        """Test internal snapshot creation with invalid format"""
        with self.assertRaises(ValueError) as context:
            _create_snapshot(1, (100, 100), "invalid")
        self.assertIn("Unsupported format", str(context.exception))

    def test_create_snapshot_internal_invalid_source_id(self):
        """Test internal snapshot creation with invalid source ID"""
        with self.assertRaises(ValueError):
            _create_snapshot(-1, (100, 100), "jpeg")

    def test_create_snapshot_internal_invalid_size(self):
        """Test internal snapshot creation with invalid size"""
        test_cases = [
            (0, 100),
            (100, 0),
            (-100, 100),
            (100, -100)
        ]
        
        for width, height in test_cases:
            with self.assertRaises(ValueError):
                _create_snapshot(1, (width, height), "jpeg")

    def test_create_snapshot_internal_traa_error(self):
        """Test internal snapshot creation when traa raises an error"""
        with patch('traa.create_snapshot') as mock_snapshot:
            mock_snapshot.side_effect = Error(22, "Invalid source ID")
            with self.assertRaises(RuntimeError) as context:
                _create_snapshot(1, (100, 100), "jpeg")
            self.assertIn("Failed to create snapshot", str(context.exception))

    def test_create_snapshot_internal_invalid_result(self):
        """Test internal snapshot creation with invalid result format"""
        with patch('traa.create_snapshot') as mock_snapshot:
            mock_snapshot.return_value = None
            with self.assertRaises(RuntimeError) as context:
                _create_snapshot(1, (100, 100), "jpeg")
            self.assertIn("Invalid result format", str(context.exception))

if __name__ == '__main__':
    # Create a test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSnapshot)
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite) 